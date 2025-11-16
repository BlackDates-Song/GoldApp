import asyncio
import pandas as pd
import akshare as ak
import yfinance as yf

from cache import cached_data

async def _get_usd_cny():
    """
    获取 USD/CNY 汇率
    """
    try:
        hist = yf.download("USDCNY=X", period="2d", interval="1d")
        if hist.empty or len(hist) < 2:
            raise Exception("yfinance 未能返回 USD/CNY 的 2 天历史数据")
        latest = hist.iloc[-1]
        previous = hist.iloc[-2]
        change_pct = ((latest['Close'] - previous['Close']) / previous['Close']) * 100
        return {
            "price": float(latest['Close']),
            "change_pct": float(change_pct)
        }
    except Exception as e:
        print(f"--- !!! [市场指标任务] 获取 USD/CNY 汇率失败: {e} !!! ---")
        return {"price": "N/A", "change_pct": 0}
    
async def _get_lpr_1y():
    """
    获取中国 1 年期 LPR
    """
    try:
        df = await asyncio.to_thread(ak.macro_china_lpr)
        if df is not None:
            latest_lpr = df.iloc[-1]['LPR1Y']
            return float(latest_lpr)
    except Exception as e:
        print(f"--- !!! [市场指标任务] 获取 1 年期 LPR 失败: {e} !!! ---")
        return "N/A"
    
async def _get_sh_index():
    """
    获取上证指数
    """
    try:
        df = await asyncio.to_thread(ak.stock_zh_index_daily, symbol="sh000001")
        if df is not None:    
            latest = df.iloc[-1]
            previous = df.iloc[-2]
            change_pct = ((latest['close'] - previous['close']) / previous['close']) * 100
            return {
                "price": float(latest['close']),
                "change_pct": float(change_pct)
            }
    except Exception as e:
        print(f"--- !!! [市场指标任务] 获取上证指数失败: {e} !!! ---")
        return {"price": "N/A", "change_pct": 0}
    
async def _get_gold_etf_holdings():
    """
    获取黄金 ETF 持仓量
    """
    try:
        df = await asyncio.to_thread(ak.macro_cons_gold)
        if df is not None:
            latest = df.iloc[-1]['总库存']
            return float(latest)
    except Exception as e:
        print(f"--- !!! [市场指标任务] 获取黄金 ETF 持仓量失败: {e} !!! ---")
        return "N/A"
    
async def fetch_and_cache_market_indicators():
    print("--- [市场指标任务] 正在加载市场指标数据... ---")
    results_list = await asyncio.gather(
        _get_usd_cny(),
        _get_lpr_1y(),
        _get_sh_index(),
        # _get_gold_etf_holdings()
    )

    results = {
        "usd_cny": results_list[0],
        "lpr_1y": results_list[1],
        "sh_index": results_list[2],
        # "gold_etf_holdings": results_list[3]
    }
    cached_data['market_indicators'] = results
    print(f"--- [市场指标任务] 市场指标数据已缓存: {results} ---")

async def update_market_indicators_periodically():
    while True:
        await asyncio.sleep(4 * 60 * 60) # 4 小时
        print("--- [定时任务] 正在刷新市场指标数据... ---")
        await fetch_and_cache_market_indicators()