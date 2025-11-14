import asyncio
import akshare as ak

from cache import cached_data

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

async def update_news_cache_periodically():
    while True:
        await asyncio.sleep(15 * 60) 
        print("--- [定时任务] 正在刷新新闻缓存... ---")
        await fetch_and_cache_news()