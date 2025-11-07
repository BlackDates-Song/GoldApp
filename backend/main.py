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

# --- 1. 缓存 (用于K线) ---
cached_data: Dict[str, Any] = {}

# --- 2. 帮助函数：格式化 K 线 (你的版本 - 很好) ---
def format_for_echarts_kline(df: pd.DataFrame) -> Dict[str, Any]:
    """
    格式化 DataFrame 为 ECharts 的 K 线和 MA 线
    (v4.14 - 修复 JSON 序列化错误: NaN/inf 全部转为 None)
    """

    # 1. 丢弃主价格列中有 NaN 的行
    df.dropna(subset=['open', 'close', 'high', 'low'], inplace=True, how='any')

    # 2. 格式化日期
    df_formatted = df.reset_index()
    df_formatted['Date'] = df_formatted['Date'].dt.strftime('%Y-%m-%d')
    dates = df_formatted['Date'].tolist()

    # 3. 统一替换 inf/-inf 为 NaN
    df_formatted.replace([np.inf, -np.inf], np.nan, inplace=True)

    # 4. 定义安全转换函数
    def safe_float_list(series: pd.Series):
        """
        将 Pandas Series 转换为 JSON 安全的 float 列表：
        - NaN / inf / -inf → None
        - float → 保留两位小数
        """
        result = []
        for v in series:
            if pd.isna(v) or v in [np.inf, -np.inf]:
                result.append(None)
            else:
                result.append(round(float(v), 2))
        return result

    # 5. 清理并提取数据
    k_line_data = df_formatted[['Date', 'open', 'close', 'low', 'high']].values.tolist()
    ma5_data = safe_float_list(df_formatted['MA5']) if 'MA5' in df_formatted else []
    ma10_data = safe_float_list(df_formatted['MA10']) if 'MA10' in df_formatted else []
    ma20_data = safe_float_list(df_formatted['MA20']) if 'MA20' in df_formatted else []

    # 7. 返回结构化数据
    return {
        "success": True,
        "dates": dates,
        "k_line_data": k_line_data,
        "ma5": ma5_data,
        "ma10": ma10_data,
        "ma20": ma20_data
    }


# --- 3. 'lifespan' (K线缓存, 不变) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global cached_data
    print("服务器启动... 正在加载 Au99.99 历史K线...")
    
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
        
        data_daily.dropna(subset=cols_to_numeric, inplace=True, how='any')

        print("正在计算均线 (MA)...")
        data_daily['MA5'] = data_daily['close'].rolling(window=5).mean()
        data_daily['MA10'] = data_daily['close'].rolling(window=10).mean()
        data_daily['MA20'] = data_daily['close'].rolling(window=20).mean()

        print("正在计算周K和月K...")
        agg_rules = { 'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last' }
        data_weekly = data_daily.resample('W').agg(agg_rules)
        data_monthly = data_daily.resample('ME').agg(agg_rules)
        
        data_weekly['MA5'] = data_weekly['close'].rolling(window=5).mean()
        data_weekly['MA10'] = data_weekly['close'].rolling(window=10).mean()
        data_weekly['MA20'] = data_weekly['close'].rolling(window=20).mean()
        
        data_monthly['MA5'] = data_monthly['close'].rolling(window=5).mean()
        data_monthly['MA10'] = data_monthly['close'].rolling(window=10).mean()
        data_monthly['MA20'] = data_monthly['close'].rolling(window=20).mean()

        print("正在格式化并缓存K线数据...")
        cached_data['daily'] = format_for_echarts_kline(data_daily.copy())
        cached_data['weekly'] = format_for_echarts_kline(data_weekly.copy())
        cached_data['monthly'] = format_for_echarts_kline(data_monthly.copy())
        
        print("--- SGE K线数据 (含MA) 已缓存！ ---")
        
    except Exception as e:
        print(f"--- !!! 启动时数据加载失败 !!! ---\n错误: {e}")
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

# --- 
# --- *** 6. 所有的 API 路由 ***
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

        # (v4.21 不变) 你的日期计算逻辑是正确的
        update_time_str = data_df.iloc[0]['更新时间']
        parsed_datetime = pd.to_datetime(update_time_str, format='%Y年%m月%d日 %H:%M:%S')
        intraday_data = []
        time_col = '时间' if '时间' in data_df.columns else 'TIME'

        for _, row in data_df.iterrows():
            time_value = row[time_col]

            if isinstance(time_value, str):
                if time_value == "24:00:00":
                    time_value = "00:00:00"
                hour, minute, second = map(int, time_value.split(":"))
            elif isinstance(time_value, datetime.time):
                hour, minute, second = time_value.hour, time_value.minute, time_value.second
                time_value = time_value.strftime("%H:%M:%S")
            else:
                continue

            current_time = pd.Timestamp(parsed_datetime.year, parsed_datetime.month, parsed_datetime.day, hour, minute, second)

            if hour < 16:
                trade_date = (current_time - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                trade_date = current_time.strftime('%Y-%m-%d')

            full_timestamp = f"{trade_date}T{time_value}"
            intraday_data.append([full_timestamp, float(row['现价'])])
        
        # --- (v4.21 关键修复) ---
        # 1. 检查列表是否为空
        if not intraday_data:
            return {"success": True, "data": []}
            
        # 2. 找到最新的交易日 (例如 "2025-11-07")
        #    item[0].split('T')[0] 会获取 'YYYY-MM-DD' 部分
        latest_date_str = max(item[0].split('T')[0] for item in intraday_data)
        
        # 3. 过滤列表，只保留最新交易日的数据
        filtered_data = [item for item in intraday_data if item[0].startswith(latest_date_str)]
        
        print(f"[调试] 找到最新交易日: {latest_date_str}, 过滤后 {len(filtered_data)} 条数据")
        # --- (修复结束) ---

        return {"success": True, "data": filtered_data} # <-- 返回过滤后的数据
    
    except Exception as e:
        import traceback
        traceback.print_exc() # 打印更详细的错误
        raise HTTPException(status_code=500, detail=f"获取分时数据失败: {e}")


@app.get("/api/gold-realtime-quote")
async def get_gold_realtime_quote():
    try:
        data_df = ak.spot_quotations_sge(symbol="Au99.99")
        if data_df.empty:
            raise HTTPException(status_code=404, detail="未返回实时数据")
        latest_quote = data_df.iloc[-1]
        
        time_col = '时间' if '时间' in latest_quote else 'TIME'
        update_time_col = '更新时间' if '更新时间' in latest_quote else 'UPDATE-TIME'

        return {
            "success": True, 
            "price": latest_quote['现价'],
            "time": latest_quote[time_col], 
            "update_time": latest_quote[update_time_col]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实时报价失败: {e}")

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