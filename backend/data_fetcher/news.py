import asyncio
import akshare as ak
import pandas as pd
from snownlp import SnowNLP

from cache import cached_data

def _fetch_news_data_sync():
    print("--- [新闻任务] 正在加载上海金属网(SHMET)快讯... ---")

    news_df_raw = ak.futures_news_shmet(symbol="贵金属") 
    if news_df_raw is None:
        return None
    
    content_col = '内容' 
    contains_gold = news_df_raw[content_col].str.contains("黄金", na=False)
    contains_silver = news_df_raw[content_col].str.contains(r"(白银|银)", na=False)
    contains_platinum = news_df_raw[content_col].str.contains(r"(铂金|铂)", na=False)
    contains_palladium = news_df_raw[content_col].str.contains(r"(钯金|钯)", na=False)
    is_other_metal_only = (contains_silver | contains_platinum | contains_palladium) & ~contains_gold
    news_df = news_df_raw[~is_other_metal_only].tail(50).copy()

    print(f"--- [新闻任务] 正在进行 NLP 情感分析 ---")

    def calculate_sentiment(text):
        try:
            return SnowNLP(text).sentiments
        except:
            return 0.5
        
    news_df['sentiment'] = news_df[content_col].apply(calculate_sentiment)
    avg_raw_score = news_df['sentiment'].mean()
    market_sentiment_index = (avg_raw_score - 0.5) * 2
    print(f"--- [新闻任务] NLP 分析完成。平均情绪: {avg_raw_score:.2f} -> 指数: {market_sentiment_index:.2f} ---")

    news_df.rename(columns={'发布时间': 'report_time', '内容': 'report_content'}, inplace=True)

    return {
        "items": news_df[['report_time', 'report_content', 'sentiment']].to_dict('records'),
        "sentiment_index": float(market_sentiment_index)
    }

async def fetch_and_cache_news():
    try:
        result = await asyncio.to_thread(_fetch_news_data_sync)
        if result is not None:
            cached_data['news'] = result
            print(f"--- [新闻任务] 贵金属快讯过滤后，已缓存 {len(cached_data['news']['items'])} 条 ---")
        else:
            if 'news' not in cached_data:
                cached_data['news'] = {"items": [], "sentiment_index": 0}

    except Exception as e:
        print(f"--- !!! [新闻任务] 快讯加载失败 !!! ---\n错误: {e}")
        if 'news' not in cached_data:
            cached_data['news'] = {"items": [], "sentiment_index": 0}

async def update_news_cache_periodically():
    while True:
        await asyncio.sleep(15 * 60) 
        print("--- [定时任务] 正在刷新新闻缓存... ---")
        await fetch_and_cache_news()