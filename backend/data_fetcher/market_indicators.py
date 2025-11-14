import asyncio
import pandas as pd
import akshare as ak

from cache import cached_data

async def _get_usd_cny():
    """
    获取 USD/CNY 汇率
    """
    try:
        df = await asyncio.to_thread(ak.forex_spot_em)
        usd_cny_data = df[df['代码'] == 'USDCHN'].iloc[0]
        return {
            "price": float(usd_cny_data['最新价']),
            "change_pct": float(usd_cny_data['涨跌幅'])
        }
    except Exception as e:
        print(f"--- !!! [市场指标任务] 获取 USD/CNY 汇率失败: {e} !!! ---")
        return {"price": "N/A", "change_pct": 0}