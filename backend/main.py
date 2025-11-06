from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import akshare as ak
import pandas as pd
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi.responses import FileResponse  # <-- *** 1. 导入这个 ***
import os # <-- 导入 os 来处理文件路径

# --- 缓存 (不变) ---
cached_data: Dict[str, Any] = {}

# --- 帮助函数：格式化 K 线 (不变) ---
def format_for_echarts_kline(df: pd.DataFrame) -> Dict[str, Any]:
    df_clean = df.dropna()
    df_formatted = df_clean.reset_index() 
    df_formatted['Date'] = df_formatted['Date'].dt.strftime('%Y-%m-%d')
    k_line_data = df_formatted[['Date', 'open', 'close', 'low', 'high']].values.tolist()
    dates = df_formatted['Date'].tolist()
    
    return {
        "success": True, "dates": dates, "k_line_data": k_line_data
    }

# --- 'lifespan' (K线缓存, 不变) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global cached_data
    print("服务器启动... 正在使用 AkShare SGE (spot_hist_sge) 加载 Au99.99 历史K线...")
    
    try:
        data_daily = ak.spot_hist_sge(symbol="Au99.99")
        if data_daily.empty:
            print("致命错误: AkShare 未能下载 SGE 'Au99.99' 历史K线。"); yield; return

        print("SGE Au99.99 历史K线下载成功！")
        
        data_daily.rename(columns={'date': 'Date', 'open': 'open', 'close': 'close', 'high': 'high', 'low': 'low'}, inplace=True)
        data_daily['Date'] = pd.to_datetime(data_daily['Date'])
        data_daily.set_index('Date', inplace=True)
        cols_to_numeric = ['open', 'close', 'high', 'low']
        data_daily[cols_to_numeric] = data_daily[cols_to_numeric].apply(pd.to_numeric, errors='coerce')

        print("正在计算周K和月K...")
        agg_rules = { 'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last' }
        data_weekly = data_daily.resample('W').agg(agg_rules)
        data_monthly = data_daily.resample('ME').agg(agg_rules)

        print("正在格式化并缓存K线数据...")
        cached_data['daily'] = format_for_echarts_kline(data_daily.copy())
        cached_data['weekly'] = format_for_echarts_kline(data_weekly.copy())
        cached_data['monthly'] = format_for_echarts_kline(data_monthly.copy())
        
        print("--- SGE K线数据已缓存！ ---")
        
    except Exception as e:
        print(f"--- !!! 启动时数据加载失败 !!! --- \n错误: {e}")
        import traceback
        traceback.print_exc()
        
    yield
    print("服务器关闭。")

# --- 创建 FastAPI 应用 (不变) ---
app = FastAPI(lifespan=lifespan)

# --- 配置 CORS (不变) ---
# (这个仍然需要, 以防万一)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- 
# --- *** 2. 定义我们的 API 路由 (K线, 分时, 实时) ***
# --- 
@app.get("/api/gold-data")
async def get_gold_data(period: str = "daily"): 
    if period not in cached_data:
        raise HTTPException(status_code=400, detail="无效的 'period' 参数。")
    if not cached_data[period]:
         raise HTTPException(status_code=500, detail="数据源错误: K线缓存未加载。")
    return cached_data[period]

@app.get("/api/gold-intraday")
async def get_gold_intraday():
    try:
        data_df = ak.spot_quotations_sge(symbol="Au99.99")
        if data_df.empty:
            return {"success": False, "data": []}
        intraday_data = []
        for index, row in data_df.iterrows():
            intraday_data.append([ row['时间'], row['现价'] ])
        return {"success": True, "data": intraday_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分时数据失败: {e}")

@app.get("/api/gold-realtime-quote")
async def get_gold_realtime_quote():
    try:
        data_df = ak.spot_quotations_sge(symbol="Au99.99")
        if data_df.empty:
            raise HTTPException(status_code=404, detail="未返回实时数据")
        latest_quote = data_df.iloc[-1]
        return {
            "success": True, "price": latest_quote['现价'],
            "time": latest_quote['时间'], "update_time": latest_quote['更新时间']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实时报价失败: {e}")

# --- 
# --- *** 3. (核心修改) 定义我们的前端路由 ***
# --- 
# (我们假设 'frontend' 文件夹在 'backend' 文件夹的上一层)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

@app.get("/")
async def read_index():
    """
    当用户访问根目录时, 返回 index.html 文件
    """
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))