from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
from contextlib import asynccontextmanager
from typing import Dict, Any

# --- 1. 缓存 (不变) ---
cached_data: Dict[str, Any] = {}

# --- 2. 帮助函数：格式化 DataFrame (不变, 仍用小写) ---
def format_for_echarts(df: pd.DataFrame) -> Dict[str, Any]:
    """
    将 Pandas DataFrame 转换为 ECharts 需要的 JSON 格式
    (使用全小写的列名)
    """
    df_clean = df.dropna()
    df_formatted = df_clean.reset_index() 
    df_formatted['Date'] = df_formatted['Date'].dt.strftime('%Y-%m-%d')

    k_line_data = df_formatted[['Date', 'open', 'close', 'low', 'high']].values.tolist()
    volume_data = df_formatted[['Date', 'volume']].values.tolist()
    dates = df_formatted['Date'].tolist()
    
    return {
        "success": True,
        "dates": dates,
        "k_line_data": k_line_data,
        "volume_data": volume_data
    }

# --- 3. 升级版的 'lifespan' (最终修复) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global cached_data
    print("服务器启动... 正在加载并处理 K 线数据...")
    try:
        # --- 1. 下载日K数据 ---
        data_daily = yf.download(tickers="518880.SS", period="max", auto_adjust=True)
        
        if data_daily.empty:
            print("警告: yfinance 未能下载日K数据。")
            yield
            return

        data_daily.index = pd.to_datetime(data_daily.index)

        # --- 
        # --- 最终修复：处理 MultiIndex 或 Index ---
        # ---
        
        # 1. 检查是不是 MultiIndex
        if isinstance(data_daily.columns, pd.MultiIndex):
            print("检测到 MultiIndex，正在平坦化...")
            # 如果是 MultiIndex [('Open', ''), ('High', '')],
            # 我们提取第0层，把它变成 ['Open', 'High']
            data_daily.columns = data_daily.columns.get_level_values(0)

        # 2. 现在，它 100% 是一个 Simple Index
        #    我们再安全地执行 .str.lower()
        print("正在将列名转为小写...")
        data_daily.columns = data_daily.columns.str.lower()
        # 现在列名绝对是: 'open', 'high', 'low', 'close', 'volume'
        
        # --- 
        # --- 修复结束 ---
        # ---

        # --- 2. 计算 周K 和 月K (使用小写) ---
        print("正在计算周K和月K...")
        agg_rules = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        data_weekly = data_daily.resample('W').agg(agg_rules)
        data_monthly = data_daily.resample('ME').agg(agg_rules)

        # --- 3. 格式化并缓存 ---
        print("正在格式化并缓存数据...")
        cached_data['daily'] = format_for_echarts(data_daily.copy())
        cached_data['weekly'] = format_for_echarts(data_weekly.copy())
        cached_data['monthly'] = format_for_echarts(data_monthly.copy())
        
        print("---")
        print("日K, 周K, 月K 数据已全部加载并缓存！")
        print("---")
        
    except Exception as e:
        print("--- !!! 启动时数据加载失败 !!! ---")
        print(f"错误: {e}")
        import traceback
        traceback.print_exc() # 打印完整的错误堆栈
        
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

# --- 6. 升级版的 K 线 API (不变) ---
@app.get("/api/gold-data")
async def get_gold_data(period: str = "daily"): 
    
    if period not in cached_data:
        valid_periods = ", ".join(cached_data.keys())
        raise HTTPException(
            status_code=400, 
            detail=f"无效的 'period' 参数。请使用: {valid_periods}"
        )
    
    if not cached_data[period]:
         raise HTTPException(
            status_code=500, 
            detail=f"数据源错误: {period} 数据未能成功加载到缓存。"
        )

    return cached_data[period]

# --- 7. (不变) ---
@app.get("/")
def read_root():
    return {"message": "欢迎来到黄金数据API v2。请访问 /api/gold-data?period=..."}