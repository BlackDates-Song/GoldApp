from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import akshare as ak
import pandas as pd
import numpy as np 
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi.responses import FileResponse
import os
import datetime
import asyncio

# --- 1. 缓存 (用于K线, 新闻, 和 宏观数据) ---
cached_data: Dict[str, Any] = {}

# --- (v4.29) 专用于分时图的精细化缓存 ---
intraday_cache = {
    "night_session": [],
    "day_session": [],
    "last_trade_date_str": None
}

# --- 2. 帮助函数：格式化 K 线 (不变) ---
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

# --- (v4.32 新增) K线加载独立函数 ---
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

# --- (v4.28) 新闻获取的独立函数 (v4.27 修复版) ---
async def fetch_and_cache_news():
    print("--- [新闻任务] 正在加载上海金属网(SHMET)快讯... ---")
    try:
        news_df_raw = await asyncio.to_thread(ak.futures_news_shmet, symbol="贵金属") 
        content_col = '内容' 
        contains_gold = news_df_raw[content_col].str.contains("黄金", na=False)
        contains_silver = news_df_raw[content_col].str.contains("白银", na=False)
        contains_platinum = news_df_raw[content_col].str.contains("铂金", na=False)
        contains_palladium = news_df_raw[content_col].str.contains("钯金", na=False)
        is_other_metal_only = (contains_silver | contains_platinum | contains_palladium) & ~contains_gold
        news_df = news_df_raw[~is_other_metal_only]
        news_df = news_df[['发布时间', '内容']].tail(50)
        news_df.rename(columns={'发布时间': 'report_time', '内容': 'report_content'}, inplace=True)
        cached_data['news'] = news_df.to_dict('records')
        print(f"--- [新闻任务] 贵金属快讯过滤后，已缓存 {len(cached_data['news'])} 条 ---")
    except Exception as e:
        print(f"--- !!! [新闻任务] 快讯加载失败 !!! ---\n错误: {e}")
        if 'news' not in cached_data:
            cached_data['news'] = []

# --- (v4.28) 后台新闻定时任务 (不变) ---
async def update_news_cache_periodically():
    while True:
        await asyncio.sleep(15 * 60) # 15 分钟
        print("--- [定时任务] 正在刷新新闻缓存... ---")
        await fetch_and_cache_news()


# --- (v4.29) 后台分时图定时任务 (不变) ---
def get_sge_trade_date_and_hour():
    now = datetime.datetime.now()
    hour = now.hour
    # 夜盘属于次日交易日
    if hour >= 20:
        trade_date = (now + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    elif hour < 8:
        trade_date = (now - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        trade_date = now.strftime('%Y-%m-%d')
    return trade_date, hour, now

async def update_intraday_cache():
    global intraday_cache
    current_trade_date, current_hour, _ = get_sge_trade_date_and_hour()

    # 初始化时不清空，只设置一次
    if intraday_cache["last_trade_date_str"] is None:
        intraday_cache["last_trade_date_str"] = current_trade_date

    # 检测新交易日 → 清空缓存
    if intraday_cache["last_trade_date_str"] != current_trade_date:
        print(f"--- [分时图任务] 检测到新交易日 {current_trade_date}，清空缓存 ---")
        intraday_cache["night_session"].clear()
        intraday_cache["day_session"].clear()
        intraday_cache["last_trade_date_str"] = current_trade_date

    # 只在交易时段更新
    if (current_hour >= 20 or current_hour < 3) or (9 <= current_hour < 16):
        try:
            data_df = await asyncio.to_thread(ak.spot_quotations_sge, symbol="Au99.99")
            if data_df.empty: return

            processed = []
            time_col = '时间' if '时间' in data_df.columns else 'TIME'
            _, _, now = get_sge_trade_date_and_hour()
            calendar_date_str = now.strftime('%Y-%m-%d')

            for _, row in data_df.iterrows():
                t = row[time_col]
                if isinstance(t, datetime.time):
                    h, m, s = t.hour, t.minute, t.second
                    time_value = t.strftime("%H:%M:%S")
                else:
                    if t == "24:00:00": t = "00:00:00"
                    h, m, s = map(int, t.split(":"))
                    time_value = t
                # 修正日期归属逻辑
                if h >= 20:
                    date_str = (now + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                elif h < 8:
                    date_str = (now - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                else:
                    date_str = calendar_date_str

                full_ts = f"{date_str}T{time_value}"
                processed.append([full_ts, float(row['现价'])])

            if not processed: return

            if (current_hour >= 20 or current_hour < 3):
                intraday_cache["night_session"] = processed
            elif (9 <= current_hour < 16):
                intraday_cache["day_session"] = processed

        except Exception as e:
            print(f"--- !!! [分时图任务] 缓存更新失败 !!! ---\n错误: {e}")


async def intraday_cache_loop():
    while True:
        await update_intraday_cache()
        await asyncio.sleep(60) # 60 秒


# --- (v4.33 优化版) 宏观数据获取函数 ---
# --- (v4.35 优化版) 宏观数据获取函数 ---
async def fetch_and_cache_global_markets():
    """
    (v4.35) 优化: 使用代码 (GC00Y, UDI) 代替名称
           并限制 bond_zh_us_rate 的日期范围
    """
    print("--- [宏观任务 v4.35] 正在加载全球市场数据... ---")
    
    results = {}
    
    # 1. 获取 XAU/USD (国际金价)
    try:
        # (v4.35 修复) 使用代码 "GC00Y"
        df = await asyncio.to_thread(ak.futures_global_hist_em, symbol="GC00Y")
        
        latest_data = df.iloc[-1]
        
        results["xau_usd"] = {
            "price": float(latest_data['最新价']),
            "change_pct": float(latest_data['涨幅']) 
        }
    except Exception as e:
        print(f"--- !!! [宏观任务] 获取 XAU/USD (GC00Y) 失败: {e} !!! ---")
        results["xau_usd"] = {"price": "N/A", "change_pct": 0}

    # 2. 获取 DXY (美元指数)
    try:
        # (v4.35 修复) 使用代码 "UDI"
        df = await asyncio.to_thread(ak.index_global_hist_em, symbol="美元指数")
        
        latest_data = df.iloc[-1]
        
        # 假设列名与 futures_global_hist_em 相同 (最新价, 涨幅)
        results["dxy"] = {
            "price": float(latest_data['最新价']),
            "change_pct": float(latest_data['振幅'])
        }
    except Exception as e:
        print(f"--- !!! [宏观任务] 获取 DXY (UDI) 失败: {e} !!! ---")
        results["dxy"] = {"price": "N/A", "change_pct": 0}

    # 3. 获取 US 10Y (美债收益率) (v4.34 逻辑不变)
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
        
        results["us_10y"] = {
            "price": price_latest,
            "change_pct": change_pct
        }
    except Exception as e:
        print(f"--- !!! [宏观任务] 获取 US 10Y 失败: {e} !!! ---")
        results["us_10y"] = {"price": "N/A", "change_pct": 0}

    cached_data['global_markets'] = results
    print(f"--- [宏观任务 v4.35] 全球市场数据已缓存: {results} ---")

# --- (v4.31) 宏观数据后台定时任务 (不变) ---
async def update_global_markets_periodically():
    while True:
        await fetch_and_cache_global_markets()
        await asyncio.sleep(10 * 60) # 每 10 分钟刷新一次


# --- 3. 'lifespan' (v4.32 - 关键修复：并行启动) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global cached_data
    print("服务器启动...")

    # 1. 定义所有 *初始* 加载任务
    task_k_lines = asyncio.create_task(fetch_and_cache_k_lines())
    task_news = asyncio.create_task(fetch_and_cache_news())
    task_intraday = asyncio.create_task(update_intraday_cache())
    task_global = asyncio.create_task(fetch_and_cache_global_markets())

    # 2. (v4.32 关键) *并行* 运行所有初始任务
    print("--- [启动] 正在并行加载所有初始数据 (K线, 新闻, 分时图, 宏观)... ---")
    await asyncio.gather(
        task_k_lines,
        task_news,
        task_intraday,
        task_global
    )
    print("--- [启动] 所有初始数据加载完毕! 服务器准备就绪。 ---")

    # 3. (v4.32 关键) *在所有数据都绪后*，再启动后台的 *定时刷新* 任务
    asyncio.create_task(update_news_cache_periodically())
    asyncio.create_task(intraday_cache_loop())
    asyncio.create_task(update_global_markets_periodically())
    
    print("--- [启动] 所有后台定时刷新任务已启动 ---")
        
    yield
    print("服务器关闭。")

# --- 4. 创建 FastAPI 应用 (不变) ---
app = FastAPI(lifespan=lifespan)
# --- 5. 配置 CORS (不变) ---
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- 
# --- *** 6. 所有的 API 路由 ***
# --- 

# ... (get_gold_data, get_gold_intraday, get_gold_realtime_quote 不变) ...
@app.get("/api/gold-data")
async def get_gold_data(period: str = "daily"): 
    if period not in cached_data: raise HTTPException(status_code=400, detail="无效的 'period' 参数。")
    if not cached_data[period]: raise HTTPException(status_code=500, detail="数据源错误: K线缓存未加载。")
    return cached_data[period]

@app.get("/api/gold-intraday")
async def get_gold_intraday():
    global intraday_cache
    try:
        combined_data = intraday_cache["night_session"] + intraday_cache["day_session"]
        if not combined_data: print("[调试] /api/gold-intraday: 缓存为空，可能在休市。")
        return {"success": True, "data": combined_data}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取分时数据失败: {e}")
    
@app.get("/api/gold-realtime-quote")
async def get_gold_realtime_quote():
    try:
        now = datetime.datetime.now(); server_update_time_str = now.strftime("%Y-%m-%d %H:%M:%S") 
        data_df = await asyncio.to_thread(ak.spot_quotations_sge, symbol="Au99.99")
        if data_df.empty: raise HTTPException(status_code=404, detail="未返回实时数据")
        latest_quote = data_df.iloc[-1]; time_col = '时间' if '时间' in latest_quote else 'TIME'
        return {"success": True, "price": latest_quote['现价'], "time": latest_quote[time_col], "update_time": server_update_time_str}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实时报价失败: {e}")

# --- (v4.30) 简单 AI API (不变) ---
@app.get("/api/ai-prediction")
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
@app.get("/api/gold-news")
async def get_gold_news():
    if "news" not in cached_data:
        raise HTTPException(status_code=500, detail="新闻数据尚未加载。")
    return {"success": True, "data": cached_data['news']}

# --- (v4.31 新增) 宏观数据 API ---
@app.get("/api/global-markets")
async def get_global_markets():
    """
    (v4.31) 从缓存中获取全球宏观指标
    """
    if "global_markets" not in cached_data:
        raise HTTPException(status_code=500, detail="全球市场数据尚未加载。")
    
    return {"success": True, "data": cached_data['global_markets']}
# --- (v4.31 结束) ---


# --- 
# --- *** 7. 定义前端路由 (不变) ***
# --- 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

@app.get("/")
async def read_index():
    html_file_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(html_file_path):
         print(f"--- 致命错误: 在这个路径找不到 index.html ---")
         print(f"--- 正在寻找: {html_file_path} ---")
         return {"message": "错误: index.html 文件未找到！", "path": html_file_path}
         
    return FileResponse(html_file_path)