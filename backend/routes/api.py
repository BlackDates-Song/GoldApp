from fastapi import APIRouter, HTTPException
import datetime
import akshare as ak
import asyncio

<<<<<<< HEAD
from cache import cached_data, intraday_cache
from utils import TZ_SHANGHAI
=======
from ..cache import cached_data, intraday_cache
from ..utils import TZ_SHANGHAI
>>>>>>> d38a5157b55ca8947f6d0e190d59cc077f78e7c5

router = APIRouter()

@router.get("/api/gold-data")
async def get_gold_data(period: str = "daily"): 
    if period not in cached_data: raise HTTPException(status_code=400, detail="无效的 'period' 参数。")
    if not cached_data[period]: raise HTTPException(status_code=500, detail="数据源错误: K线缓存未加载。")
    return cached_data[period]

@router.get("/api/gold-intraday")
async def get_gold_intraday():
    global intraday_cache
    try:
        combined_data = intraday_cache["night_session"] + intraday_cache["day_session"]
        if not combined_data: print("[调试] /api/gold-intraday: 缓存为空，可能在休市。")
        return {"success": True, "data": combined_data}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取分时数据失败: {e}")
    
@router.get("/api/gold-realtime-quote")
async def get_gold_realtime_quote():
    try:
        now = datetime.datetime.now(TZ_SHANGHAI); server_update_time_str = now.strftime("%Y-%m-%d %H:%M:%S") 
        data_df = await asyncio.to_thread(ak.spot_quotations_sge, symbol="Au99.99")
        if data_df.empty: raise HTTPException(status_code=404, detail="未返回实时数据")
        latest_quote = data_df.iloc[-1]; time_col = '时间' if '时间' in latest_quote else 'TIME'
        return {"success": True, "price": latest_quote['现价'], "time": latest_quote[time_col], "update_time": server_update_time_str}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实时报价失败: {e}")

# --- (v4.30) 简单 AI API (不变) ---
@router.get("/api/ai-prediction")
async def get_ai_prediction():
    try:
        if "daily" not in cached_data or not cached_data["daily"].get("ma5"):
             raise HTTPException(status_code=500, detail="AI模型数据尚未加载")
        ma5_list = cached_data["daily"]["ma5"]; ma20_list = cached_data["daily"]["ma20"]
        ma5_valid = [v for v in ma5_list if v is not None]; ma20_valid = [v for v in ma20_list if v is not None]
        if len(ma5_valid) < 2 or len(ma20_valid) < 2:
            return {"signal": "等待数据", "detail": "均线数据不足"}
        ma5_prev, ma5_last = ma5_valid[-2], ma5_valid[-1]; ma20_prev, ma20_last = ma20_valid[-2], ma20_valid[-1]
        signal = "震荡"; detail = f"MA5({ma5_last}) / MA20({ma20_last})"
        if ma5_prev < ma20_prev and ma5_last > ma20_last:
            signal = "看涨"; detail = f"金叉形成: MA5({ma5_last}) 上穿 MA20({ma20_last})"
        elif ma5_prev > ma20_prev and ma5_last < ma20_last:
            signal = "看跌"; detail = f"死叉形成: MA5({ma5_last}) 下穿 MA20({ma20_last})"
        elif ma5_last > ma20_last:
            signal = "多头趋势"; detail = f"MA5({ma5_last}) 保持在 MA20({ma20_last}) 之上"
        elif ma5_last < ma20_last:
            signal = "空头趋势"; detail = f"MA5({ma5_last}) 保持在 MA20({ma20_last}) 之下"
        return {"signal": signal, "detail": detail}
    except Exception as e:
        return {"signal": "错误", "detail": str(e)}

# --- (v4.28) 新闻 API (不变) ---
@router.get("/api/gold-news")
async def get_gold_news():
    if "news" not in cached_data:
        raise HTTPException(status_code=500, detail="新闻数据尚未加载。")
    return {"success": True, "data": cached_data['news']}

# --- (v4.31 新增) 宏观数据 API ---
@router.get("/api/global-markets")
async def get_global_markets():
    """
    (v4.31) 从缓存中获取全球宏观指标
    """
    if "global_markets" not in cached_data:
        raise HTTPException(status_code=500, detail="全球市场数据尚未加载。")
    
    return {"success": True, "data": cached_data['global_markets']}

# --- (v4.41 新增) 国内宏观 API ---
@router.get("/api/domestic-macro")
async def get_domestic_macro():
    """
    (v4.41) 从缓存中获取国内宏观指标
    """
    if "domestic_macro" not in cached_data or not cached_data.get("domestic_macro"):
        raise HTTPException(status_code=503, detail="国内宏观数据正在加载中。")
    
    return {"success": True, "data": cached_data['domestic_macro']}