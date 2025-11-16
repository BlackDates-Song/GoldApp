import asyncio
import pandas as pd
import akshare as ak

from cache import cached_data
from utils import akshare_retry_wrapper

# --- 辅助函数 (同步) ---
def _get_gold_etf_holdings():
    """获取 黄金ETF总持仓 (SPDR) - 这是同步的"""
    try:
        # [v4.98] 这个接口极不稳定，必须使用重试
        df = akshare_retry_wrapper(ak.macro_cons_gold)
        if df is not None:
            return float(df.iloc[-1]['总库存'])
        else:
            raise Exception("macro_cons_gold 返回空数据")
    except Exception as e:
        print(f"--- !!! [数据处理] 黄金ETF (SPDR) 失败: {e} !!! ---")
        return "N/A"

# --- 主函数 (异步) ---
async def fetch_and_cache_spdr_gold():
    print("--- [SPDR黄金 v4.98] 正在后台加载SPDR黄金数据... ---")
    
    result = await asyncio.to_thread(_get_gold_etf_holdings)
    
    cached_data['spdr_gold'] = result
    print(f"--- [SPDR黄金 v4.98] SPDR黄金数据已缓存: {result} ---")

# --- 定时任务 (异步) ---
async def update_spdr_gold_periodically():
    while True:
        # SPDR 数据每天只更新一次
        await asyncio.sleep(12 * 60 * 60) # 12 小时
        print("--- [定时任务] 正在刷新SPDR黄金数据... ---")
        await fetch_and_cache_spdr_gold()