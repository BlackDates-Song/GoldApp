from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf  # <--- 我们换回 yfinance
import pandas as pd
from contextlib import asynccontextmanager

# --- 数据缓存 ---
cached_data = {
    "data": pd.DataFrame(),
    "last_updated": None
}

# --- FastAPI 生命周期事件 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 服务器启动时执行 ---
    print("服务器启动... 正在使用 yfinance 加载初始数据...")
    try:
        #
        # --- 关键修改：使用 yfinance 下载数据 ---
        # "518880.SS" 是华安黄金ETF在雅虎财经的代码
        # period="max" 下载所有历史数据
        # auto_adjust=True 自动处理复权
        #
        data = yf.download(tickers="518880.SS", period="max", auto_adjust=True)
        
        if data.empty:
            print("警告: 启动时未能从 yfinance 加载数据。")
        else:
            # --- 数据格式化 (yfinance 的格式) ---
            data.reset_index(inplace=True) # yfinance 的 Date 默认在索引里
            data.rename(columns={
                'Date': 'Date',   # 'Date' 本来就有
                'Open': 'Open',   # 'Open' 本来就有
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume' # 'Volume' 本来就有
            }, inplace=True)
            
            # 把日期转为 ECharts 需要的 'YYYY-MM-DD' 字符串格式
            data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')
            
            cached_data["data"] = data
            cached_data["last_updated"] = pd.Timestamp.now()
            print("数据加载并缓存成功！")
            
    except Exception as e:
        print(f"启动时 yfinance 数据加载失败: {e}")
        
    yield
    # --- 服务器关闭时执行 ---
    print("服务器关闭。")

# --- 创建 FastAPI 应用 ---
app = FastAPI(lifespan=lifespan)

# --- 配置 CORS 跨域 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- API 端点 (和之前完全一样) ---
@app.get("/api/gold-data")
async def get_gold_data():
    """
    提供黄金ETF (518880.SS) 的K线数据 (来自 yfinance 缓存)
    """
    if cached_data["data"].empty:
        # 如果启动时加载失败，尝试在这里再加载一次 (作为后备)
        print("缓存为空，尝试同步加载数据...")
        try:
            data = yf.download(tickers="518880.SS", period="max", auto_adjust=True)
            if data.empty:
                raise HTTPException(status_code=504, detail="数据源当前不可用(yfinance)。")
            data.reset_index(inplace=True)
            data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')
            cached_data["data"] = data # 存入缓存
            print("后备加载成功。")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"数据加载失败: {e}")

    # 把 Pandas DataFrame 转换为 ECharts 需要的 JSON 格式
    df = cached_data["data"]
    
    k_line_data = df[['Date', 'Open', 'Close', 'Low', 'High']].values.tolist()
    volume_data = df[['Date', 'Volume']].values.tolist()
    dates = df['Date'].tolist()
    
    return {
        "success": True,
        "dates": dates,
        "k_line_data": k_line_data,
        "volume_data": volume_data
    }

@app.get("/")
def read_root():
    return {"message": "欢迎来到黄金数据API，请访问 /api/gold-data 获取数据"}