import streamlit as st
import yfinance as yf  # 重新用 yfinance
import plotly.graph_objects as go
import pandas as pd

# --- 页面基础设置 ---
st.set_page_config(page_title="国内黄金ETF价格查看器", layout="wide")
st.title("📈 国内黄金ETF (518880.SS) 价格走势图")
st.write("数据来源: 雅虎财经 (Yahoo Finance)")

# --- 侧边栏：用户输入 ---
st.sidebar.header("选项")

# 让用户选择时间范围
time_period = st.sidebar.selectbox(
    "选择时间范围:",
    ["1个月", "3个月", "6个月", "1年", "2年", "5年", "最大"],
    index=3  # 默认选中 "1年"
)

# 将用户选择转换为 yfinance 需要的参数
period_map = {
    "1个月": "1mo",
    "3个月": "3mo",
    "6个月": "6mo",
    "1年": "1y",
    "2年": "2y",
    "5年": "5y",
    "最大": "max"
}
selected_period = period_map[time_period]

# --- 数据获取 ---
ticker = '518880.SS'  # <-- 关键在这里：使用华安黄金ETF（A股上市，人民币计价）
st.sidebar.write(f"当前标的: {ticker} (华安黄金ETF)")

# 使用 yfinance 下载数据
@st.cache_data  # 缓存数据
def load_data(ticker, period):
    # 增加 auto_adjust=True 来消除那个 FutureWarning
    data = yf.download(ticker, period=period, interval="1d", auto_adjust=True) 
    if data.empty:
        st.error(f"无法下载 {ticker} 的数据，请检查标的代码或网络。")
        return pd.DataFrame() 
    data.reset_index(inplace=True) # 将日期从索引变为列
    return data

data = load_data(ticker, selected_period)

if not data.empty:
    # --- 绘制K线图 ---
    st.header("K线图 (Candlestick Chart)")
    
    # 注意：因为 auto_adjust=True，yfinance 会自动处理复权
    # 它返回的列名就是 'Open', 'High', 'Low', 'Close'
    # 并且已经没有 'Adj Close'
    
    fig = go.Figure(data=[go.Candlestick(
        x=data['Date'],
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name="K线"
    )])
    
    # 添加成交量
    fig.add_trace(go.Bar(
        x=data['Date'], 
        y=data['Volume'], 
        name="成交量",
        yaxis='y2', # 将成交量放在第二个y轴
        marker_color='rgba(100,100,100,0.3)'
    ))
    
    # K线图美化
    fig.update_layout(
        title=f"{ticker} 价格 (CNY) 与成交量",
        xaxis_title="日期",
        yaxis_title="价格 (CNY)",
        yaxis2=dict(
            title="成交量",
            overlaying='y',
            side='right',
            showgrid=False
        ),
        xaxis_rangeslider_visible=False, # 隐藏底部的范围滑块
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # 使用Streamlit显示图表
    st.plotly_chart(fig, use_container_width=True)
    
    
    # --- 显示原始数据 ---
    if st.checkbox("显示原始数据 (最近50条)"):
        st.subheader("原始数据 (按时间倒序)")
        # .tail(50) 取最后50条, .iloc[::-1] 将这50条反转
        st.dataframe(data.tail(50).iloc[::-1])
else:
    st.warning("数据为空，无法显示图表。")