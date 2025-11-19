import asyncio
import pandas as pd
import akshare as ak
import yfinance as yf
import traceback
import pandas_ta as ta
import chinese_calendar
from datetime import date

from cache import cached_data
from utils import format_for_echarts_kline

def _fetch_kline_data_sync():
    """
    (v4.32) 获取 K 线数据
    """
    print("--- [K线任务] 正在加载 Au99.99 历史K线... ---")
    try:
        # 1. 下载数据 (使用 to_thread 避免阻塞)
        data_daily = ak.spot_hist_sge(symbol="Au99.99")
        if data_daily is None:
            raise Exception("--- !!! [K线任务] AkShare 未能下载 SGE 'Au99.99' 历史K线。 ---"); return

        print("--- [K线任务] SGE Au99.99 历史K线下载成功！ ---")
        
        # 2. 数据处理
        data_daily.rename(columns={'date': 'Date', 'open': 'open', 'close': 'close', 'high': 'high', 'low': 'low'}, inplace=True)
        data_daily['Date'] = pd.to_datetime(data_daily['Date'])
        data_daily.set_index('Date', inplace=True)
        cols_to_numeric = ['open', 'close', 'high', 'low']
        data_daily[cols_to_numeric] = data_daily[cols_to_numeric].apply(pd.to_numeric, errors='coerce')
        data_daily.dropna(subset=cols_to_numeric, inplace=True, how='any')

        print("--- [K线任务] 正在获取 XAU/USD 和  USD/CNY 用于特征对齐---")
        try:
            start_date = data_daily.index[0].strftime('%Y-%m-%d')
            tickers = ["GC=F", "USDCNY=X"]
            external_data = yf.download(tickers, start=start_date, interval="1d", progress=False)['Close']
            external_data.index = external_data.index.tz_localize(None)

            data_daily = data_daily.join(external_data["GC=F"].rename('xau_usd'), how='left')
            data_daily = data_daily.join(external_data["USDCNY=X"].rename('usd_cny'), how='left')

            data_daily['xau_usd'] = data_daily['xau_usd'].ffill()
            data_daily['usd_cny'] = data_daily['usd_cny'].ffill()
        except Exception as e:
            print(f"--- !!! [K线任务] 获取 XAU/USD 和 USD/CNY 失败: {e} !!! ---")
            data_daily['xau_usd'] = None
            data_daily['usd_cny'] = None

        print("--- [K线任务] 正在计算特征工程... ---")
        data_daily['xau_cny_derived'] = data_daily['xau_usd'] * data_daily['usd_cny']
        data_daily['gold_spread'] = data_daily['close'] - (data_daily['xau_cny_derived'] / 31.1035)

        print("--- [K线任务] 正在计算均线 (MA)... ---")
        data_daily['MA5'] = data_daily['close'].rolling(window=5).mean()
        data_daily['MA10'] = data_daily['close'].rolling(window=10).mean()
        data_daily['MA20'] = data_daily['close'].rolling(window=20).mean()

        print("--- [K线任务] 正在计算14日RSI... ---")
        data_daily['rsi_14'] =data_daily.ta.rsi(length=14) 

        print("--- [K线任务] 正在计算金价涨跌幅 ---")
        data_daily['gold_return'] = data_daily['close'].pct_change()

        print("--- [K线任务] 正在计算黄金日波幅... ---")
        prev_close = data_daily['close'].shift(1)
        data_daily['gold_volatility'] = (data_daily['high'] - data_daily['low']) / prev_close

        def get_holiday_flag(day):
            day_date = day.date()
            if chinese_calendar.is_holiday(day_date):
                return 1  # 法定节假日
            elif chinese_calendar.is_workday(day_date):
                if day_date.weekday() >= 5:
                    return -1  # 调休工作日
            return 0  # 正常工作日
        
        data_daily['holiday_flag'] = data_daily.index.to_series().apply(get_holiday_flag)

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

        data_ai_features = data_daily.dropna()

        return {
            'chart_daily': format_for_echarts_kline(data_daily.copy()),
            'chart_weekly': format_for_echarts_kline(data_weekly.copy()),
            'chart_monthly': format_for_echarts_kline(data_monthly.copy()),
            'ai_features': data_ai_features.to_json(orient='records')
        }
        
    except Exception as e:
        print(f"--- !!! [K线任务] K线加载失败 !!! ---\n错误: {e}")
        traceback.print_exc()

async def fetch_and_cache_k_lines():
    global cached_data
    try:
        kline_results = await asyncio.to_thread(_fetch_kline_data_sync)

        if kline_results:
            cached_data['daily'] = kline_results['chart_daily']
            cached_data['weekly'] = kline_results['chart_weekly']
            cached_data['monthly'] = kline_results['chart_monthly']
            cached_data['ai_features'] = kline_results['ai_features']

            print("--- [K线任务] SGE K线数据 (含MA) 已缓存 ---")
            print(f"--- [K线任务] AI 特征数据已计算并缓存 ---")
        else:
            raise Exception("K线结果为空")

    except Exception as e:
        print(f"--- !!! [K线任务] K线缓存失败: {e} !!! ---")
        traceback.print_exc()