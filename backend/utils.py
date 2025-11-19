import pytz
import pandas as pd
import numpy as np
import datetime
import asyncio
import traceback
import functools
import time
import os
import psutil

from typing import Dict, Any

# --- (v4.49 新增) 定义上海时区 ---
TZ_SHANGHAI = pytz.timezone('Asia/Shanghai')

# --- 帮助函数：格式化 K 线 ---
def format_for_echarts_kline(df: pd.DataFrame) -> Dict[str, Any]:
    df.dropna(subset=['open', 'close', 'high', 'low'], inplace=True, how='any')
    df_formatted = df.reset_index()
    df_formatted['Date'] = df_formatted['Date'].dt.strftime('%Y-%m-%d')
    dates = df_formatted['Date'].tolist()
    df_formatted.replace([np.inf, -np.inf], np.nan, inplace=True)

    def safe_float_list(series: pd.Series):
        result = []
        for v in series:
            if pd.isna(v) or v in [np.inf, -np.inf]:
                result.append(None)
            else:
                result.append(round(float(v), 2))
        return result

    k_line_data = df_formatted[['Date', 'open', 'close', 'low', 'high']].values.tolist()
    ma5_data = safe_float_list(df_formatted['MA5']) if 'MA5' in df_formatted else []
    ma10_data = safe_float_list(df_formatted['MA10']) if 'MA10' in df_formatted else []
    ma20_data = safe_float_list(df_formatted['MA20']) if 'MA20' in df_formatted else []

    return {
        "success": True, "dates": dates, "k_line_data": k_line_data,
        "ma5": ma5_data, "ma10": ma10_data, "ma20": ma20_data
    }

# --- 帮助函数：获取 SGE 交易时间和日期 ---
def get_sge_trade_date_and_hour():
    now = datetime.datetime.now(TZ_SHANGHAI)
    hour = now.hour
    # 夜盘属于次日交易日
    if hour >= 20:
        trade_date = (now + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    elif hour < 8:
        trade_date = (now - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        trade_date = now.strftime('%Y-%m-%d')
    return trade_date, hour, now

def akshare_retry_wrapper(ak_function, *args, **kwargs):
    """
    (v4.81)
    通用的 AkShare *同步* 重试辅助函数。
    - 它是一个阻塞函数，应该在 asyncio.to_thread 中运行。
    """
    max_retries = 3
    retry_delay_seconds = 5
    
    func_name = ak_function.__name__
    
    for attempt in range(max_retries):
        try:
            result = ak_function(*args, **kwargs)
            
            if result is None or (hasattr(result, 'empty') and result.empty):
                raise Exception(f"{func_name} 返回了空数据 (None or empty DataFrame)")
            
            print(f"   [Akshare Wrapper] {func_name} 获取成功。")
            return result
        
        except Exception as e:
            print(f"--- !!! [Akshare Wrapper] {func_name} 失败 (尝试 {attempt + 1}/{max_retries}) !!! ---")
            print(f"--- 错误: {e} ---")
            if attempt < max_retries - 1:
                print(f"--- 将在 {retry_delay_seconds} 秒后重试... ---")
                time.sleep(retry_delay_seconds) 
            else:
                print(f"--- !!! [Akshare Wrapper] 达到最大重试次数，{func_name} 失败 !!! ---")
                return None
            
def log_memory(tag=""):
    process = psutil.Process(os.getpid())
    mb = process.memory_info().rss / 1024 / 1024
    print(f"--- [MEMORY] {tag} 当前占用: {mb:.2f} MB ---")