import asyncio
import akshare as ak
import pandas as pd
import gc
from utils import log_memory


from cache import cached_data

def _fetch_news_data_sync():
    print("--- [新闻任务] 正在加载上海金属网(SHMET)快讯... ---")

    log_memory("新闻数据获取开始")
    news_df_raw = ak.futures_news_shmet(symbol="贵金属") 
    log_memory("新闻数据获取接口访问结束")
    if news_df_raw is None:
        return None
    
    log_memory("新闻数据处理开始")
    content_col = '内容' 
    contains_gold = news_df_raw[content_col].str.contains("黄金", na=False)
    contains_silver = news_df_raw[content_col].str.contains(r"(白银|银)", na=False)
    contains_platinum = news_df_raw[content_col].str.contains(r"(铂金|铂)", na=False)
    contains_palladium = news_df_raw[content_col].str.contains(r"(钯金|钯)", na=False)
    is_other_metal_only = (contains_silver | contains_platinum | contains_palladium) & ~contains_gold
    news_df = news_df_raw[~is_other_metal_only].tail(12).copy()
    log_memory("新闻数据处理结束")

    del news_df_raw
    gc.collect()
    
    if '发布时间' in news_df.columns: news_df.rename(columns={'发布时间': 'report_time'}, inplace=True)
    if '内容' in news_df.columns: news_df.rename(columns={'内容': 'report_content'}, inplace=True)

    return news_df.to_dict('records')

async def fetch_and_cache_news():
    try:
        news_items = await asyncio.to_thread(_fetch_news_data_sync)
        if news_items:
            cached_data['news'] = {"items": news_items}
            print(f"--- [新闻任务] 完成: 已缓存 {len(news_items)} 条新闻 ---")

    except Exception as e:
        print(f"--- !!! [新闻任务] 失败 !!! ---\n错误: {e}")
        if 'news' not in cached_data:
             cached_data['news'] = {"items": []}

async def update_news_cache_periodically():
    while True:
        await asyncio.sleep(15 * 60) 
        print("--- [定时任务] 正在刷新新闻缓存... ---")
        await fetch_and_cache_news()