import asyncio
import pandas as pd
import akshare as ak
import datetime

from cache import cached_data

async def _get_xau_usd():
    """
    获取 XAU/USD 国际金价
    """
    try:
        df = await asyncio.to_thread(ak.futures_global_spot_em)
        xau_usd_data = df[df['代码'] == 'GC00Y'].iloc[0]
        return {
            "price": float(xau_usd_data['最新价']),
            "change_pct": float(xau_usd_data['涨跌幅']) 
        }
    except Exception as e:
        print(f"--- !!! [国际市场任务] 获取 XAU/USD (GC00Y) 失败: {e} !!! ---")
        return {"price": "N/A", "change_pct": 0}

async def _get_dxy():
    """
    获取 DXY 美元指数
    """
    try:
        df = await asyncio.to_thread(ak.index_global_spot_em)
        dxy_data = df[df['代码'] == 'UDI'].iloc[0]
        return {
            "price": float(dxy_data['最新价']),
            "change_pct": float(dxy_data['振幅'])
        }
    except Exception as e:
        print(f"--- !!! [国际市场任务] 获取 DXY (UDI) 失败: {e} !!! ---")
        return {"price": "N/A", "change_pct": 0}
    
async def _get_us_10y():
    """
    获取 US 10Y 美债收益率
    """
    try:
        start_date = (datetime.datetime.now() - datetime.timedelta(days=14)).strftime('%Y%m%d')
        df = await asyncio.to_thread(ak.bond_zh_us_rate, start_date=start_date) #
        valid_df = df.dropna(subset=['美国国债收益率10年']).tail(2) #
        if len(valid_df) < 2:
            raise Exception("美债数据不足，无法计算涨跌")
        latest = valid_df.iloc[-1]
        previous = valid_df.iloc[-2]
        price_latest = float(latest['美国国债收益率10年']) #
        price_previous = float(previous['美国国债收益率10年']) #
        change_pct = ((price_latest - price_previous) / price_previous) * 100
        return {
            "price": price_latest,
            "change_pct": change_pct
        }
    except Exception as e:
        print(f"--- !!! [国际市场任务] 获取 US 10Y 失败: {e} !!! ---")
        return {"price": "N/A", "change_pct": 0}
    
async def fetch_and_cache_global_markets():
    print("--- [国际市场任务] 正在加载全球市场数据... ---")
    
    results_list = await asyncio.gather(
        _get_xau_usd(),
        _get_dxy(),
        _get_us_10y()
    )
    
    results = {
        "xau_usd": results_list[0],
        "dxy": results_list[1],
        "us_10y": results_list[2]
    }
    
    cached_data['global_markets'] = results
    print(f"--- [国际市场任务] 全球市场数据已缓存: {results} ---")

async def update_global_markets_periodically():
    while True:
        await asyncio.sleep(15 * 60) # 每15分钟刷新一次
        print("--- [定时任务] 正在刷新全球市场数据... ---")
        await fetch_and_cache_global_markets()