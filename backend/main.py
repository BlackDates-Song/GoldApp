from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import akshare as ak
import pandas as pd
from contextlib import asynccontextmanager
from typing import Dict, Any
import json # 用于S理 Pnadas 的 JSON S换

# --- 1. 缓存 (不变) ---
cached_data: Dict[str, Any] = {}

# --- 2. 帮助函数：格式化 DataFrame (不变) ---
def format_for_echarts(df: pd.DataFrame) -> Dict[str, Any]:
    df_clean = df.dropna()
    df_formatted = df_clean.reset_index() 
    df_formatted['Date'] = df_formatted['Date'].dt.strftime('%Y-%m-%d')
    k_line_data = df_formatted[['Date', 'open', 'close', 'low', 'high']].values.tolist()
    dates = df_formatted['Date'].tolist()
    
    return {
        "success": True,
        "dates": dates,
        "k_line_data": k_line_data
    }

# --- 3. 'lifespan' (SGE 最终版, 不变) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global cached_data
    print("服务器启动... 正在使用 AkShare SGE (spot_hist_sge) 加载 Au99.99 数据...")
    
    try:
        data_daily = ak.spot_hist_sge(symbol="Au99.99")
        if data_daily.empty:
            print("致命错误: AkShare 未能下载 SGE 'Au99.99' 数据。")
            yield
            return

        print("SGE Au99.99 数据下载成功！")
        
        data_daily.rename(columns={
            'date': 'Date', 'open': 'open', 'close': 'close',
            'high': 'high', 'low': 'low'
        }, inplace=True)
        
        data_daily['Date'] = pd.to_datetime(data_daily['Date'])
        data_daily.set_index('Date', inplace=True)
        
        cols_to_numeric = ['open', 'close', 'high', 'low']
        data_daily[cols_to_numeric] = data_daily[cols_to_numeric].apply(pd.to_numeric, errors='coerce')

        print("正在计算周K和月K...")
        agg_rules = {
            'open': 'first', 'high': 'max',
            'low': 'min', 'close': 'last'
        }
        data_weekly = data_daily.resample('W').agg(agg_rules)
        data_monthly = data_daily.resample('ME').agg(agg_rules)

        print("正在格式化并缓存数据...")
        cached_data['daily'] = format_for_echarts(data_daily.copy())
        cached_data['weekly'] = format_for_echarts(data_weekly.copy())
        cached_data['monthly'] = format_for_echarts(data_monthly.copy())
        
        print("---")
        print("SGE 日K, 周K, 月K 数据已全部加载并缓存！")
        print("---")
        
    except Exception as e:
        print("--- !!! 启动时数据加载失败 !!! ---")
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        
    yield
    print("服务器关闭。")

# --- 4. 创建 FastAPI 应用 (不变) ---
app = FastAPI(lifespan=lifespan)

# --- 5. 配置 CORS (不变) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- 6. K 线 API (不变) ---
@app.get("/api/gold-data")
async def get_gold_data(period: str = "daily"): 
    if period not in cached_data:
        raise HTTPException(status_code=400, detail="无效的 'period' 参数。")
    if not cached_data[period]:
         raise HTTPException(status_code=500, detail="数据源错误: 缓存未加载。")
    return cached_data[period]

#
# --- *** 7. 我们S加的“侦察”API *** ---
#
@app.get("/api/debug-realtime")
async def get_realtime_debug_data():
    """
    (调试用) 实时调用 SGE 实时行情接口并返回原始数据
    """
    print("--- 调试 --- 收到 /api/debug-realtime 请求")
    try:
        # 1. 实时调用你找到的接口
        data = ak.spot_quotations_sge(symbol="Au99.99")
        
        if data.empty:
            return {"message": "AkShare 返回了空数据"}
            
        # 2. 在S端打印出列名, 供我们自己看
        print(f"--- 调试 --- 原始列名: {data.columns}")
        
        # 3. 把S据转为 JSON (records 格式是一个列表)
        #    并直接返回给你的浏览器
        return data.to_dict(orient="records")
        
    except Exception as e:
        print(f"--- 调试 --- 接口调用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
#
# --- *** 调试 API 结束 *** ---
#

# --- 8. (不变) ---
@app.get("/")
def read_root():
    return {"message": "欢迎来到黄金数据API v3 (SGE Au99.99)"}