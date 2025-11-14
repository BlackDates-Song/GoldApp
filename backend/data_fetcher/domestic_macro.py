import asyncio
import pandas as pd
import akshare as ak

from cache import cached_data

async def _get_cpi_yoy():
    """
    获取中国 CPI 同比数据
    """
    try:
        df = await asyncio.to_thread(ak.macro_china_cpi)
        if df is not None:
            latest_cpi = df.iloc[0]['全国-同比增长']
            return float(latest_cpi)  
    except Exception as e:
        print(f"--- !!! [国内宏观任务] 获取 CPI 失败: {e} !!! ---")
        return "N/A"
    
async def _get_ppi_yoy():
    """
    获取中国 PPI 同比数据
    """
    try:
        df = await asyncio.to_thread(ak.macro_china_ppi)
        if df is not None:
            latest_ppi = df.iloc[0]['当月同比增长']
            return float(latest_ppi)
    except Exception as e:
        print(f"--- !!! [国内宏观任务] 获取 PPI 失败: {e} !!! ---")
        return "N/A"
    
async def _get_m2_yoy():
    """
    获取中国 M2 同比数据
    """
    try:
        df = await asyncio.to_thread(ak.macro_china_money_supply)
        if df is not None:
            latest_m2 = df.iloc[0]['货币和准货币(M2)-同比增长']
            return float(latest_m2)
    except Exception as e:
        print(f"--- !!! [国内宏观任务] 获取 M2 失败: {e} !!! ---")
        return "N/A"
    
async def _get_gdp_yoy():
    """
    获取中国 GDP 同比数据
    """
    try:
        df = await asyncio.to_thread(ak.macro_china_gdp)
        if df is not None:
            latest_gdp = df.iloc[0]['国内生产总值-同比增长']
            return float(latest_gdp)
    except Exception as e:
        print(f"--- !!! [国内宏观任务] 获取 GDP 失败: {e} !!! ---")
        return "N/A"

async def fetch_and_cache_domestic_macro():
    print("--- [国内宏观任务] 正在加载国内宏观数据... ---")
    results_list = await asyncio.gather(
        _get_cpi_yoy(),
        _get_ppi_yoy(),
        _get_m2_yoy(),
        _get_gdp_yoy()
    )

    results = {
        "cpi_yoy": results_list[0],
        "ppi_yoy": results_list[1],
        "m2_yoy": results_list[2],
        "gdp_yoy": results_list[3]
    }
    cached_data['domestic_macro'] = results
    print(f"--- [国内宏观任务] 国内宏观数据已缓存: {results} ---")

async def update_domestic_macro_periodically():
    while True:
        await asyncio.sleep(24 * 60 * 60) # 24 小时
        print("--- [定时任务] 正在刷新国内宏观数据... ---")
        await fetch_and_cache_domestic_macro()