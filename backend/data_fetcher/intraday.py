import asyncio
import akshare as ak
import datetime

from cache import intraday_cache
from utils import get_sge_trade_date_and_hour

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
            if data_df is None: 
                print("--- !!! [分时图任务] AkShare 未能下载 SGE 'Au99.99' 分时数据。 ---")
                return

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