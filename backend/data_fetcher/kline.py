import asyncio
import pandas as pd
import akshare as ak
import traceback

from cache import cached_data
from utils import format_for_echarts_kline

async def fetch_and_cache_k_lines():
    """
    (v4.32) 独立获取并缓存 K 线数据
    """
    global cached_data
    print("--- [K线任务] 正在加载 Au99.99 历史K线... ---")
    try:
        # 1. 下载数据 (使用 to_thread 避免阻塞)
        data_daily = await asyncio.to_thread(ak.spot_hist_sge, symbol="Au99.99")
        if data_daily.empty:
            print("--- !!! [K线任务] AkShare 未能下载 SGE 'Au99.99' 历史K线。 ---"); return

        print("--- [K线任务] SGE Au99.99 历史K线下载成功！ ---")
        
        # 2. 数据处理
        data_daily.rename(columns={'date': 'Date', 'open': 'open', 'close': 'close', 'high': 'high', 'low': 'low'}, inplace=True)
        data_daily['Date'] = pd.to_datetime(data_daily['Date'])
        data_daily.set_index('Date', inplace=True)
        cols_to_numeric = ['open', 'close', 'high', 'low']
        data_daily[cols_to_numeric] = data_daily[cols_to_numeric].apply(pd.to_numeric, errors='coerce')
        data_daily.dropna(subset=cols_to_numeric, inplace=True, how='any')

        print("--- [K线任务] 正在计算均线 (MA)... ---")
        data_daily['MA5'] = data_daily['close'].rolling(window=5).mean()
        data_daily['MA10'] = data_daily['close'].rolling(window=10).mean()
        data_daily['MA20'] = data_daily['close'].rolling(window=20).mean()

        print("--- [K线任务] 正在计算周K和月K... ---")
        agg_rules = { 'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last' }
        data_weekly = data_daily.resample('W').agg(agg_rules)
        data_monthly = data_daily.resample('ME').agg(agg_rules)
        
        data_weekly['MA5'] = data_weekly['close'].rolling(window=5).mean()
        data_weekly['MA10'] = data_weekly['close'].rolling(window=10).mean()
        data_weekly['MA20'] = data_weekly['close'].rolling(window=20).mean()
        
        data_monthly['MA5'] = data_monthly['close'].rolling(window=5).mean()
        data_monthly['MA10'] = data_monthly['close'].rolling(window=10).mean()
        data_monthly['MA20'] = data_monthly['close'].rolling(window=20).mean()

        print("--- [K线任务] 正在格式化并缓存K线数据... ---")
        cached_data['daily'] = format_for_echarts_kline(data_daily.copy())
        cached_data['weekly'] = format_for_echarts_kline(data_weekly.copy())
        cached_data['monthly'] = format_for_echarts_kline(data_monthly.copy())
        
        print("--- [K线任务] SGE K线数据 (含MA) 已缓存！ ---")
        
    except Exception as e:
        print(f"--- !!! [K线任务] K线加载失败 !!! ---\n错误: {e}")
        import traceback
        traceback.print_exc()