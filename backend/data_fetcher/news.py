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
    news_df = news_df_raw[~is_other_metal_only].tail(20).copy()
    
    if '发布时间' in news_df.columns: news_df.rename(columns={'发布时间': 'report_time'}, inplace=True)
    if '内容' in news_df.columns: news_df.rename(columns={'内容': 'report_content'}, inplace=True)
    
    return news_df.to_dict('records')

def _analyze_sentiment_sync(news_items):
    print(f"--- [新闻任务] 正在进行 NLP 情感分析 ---")
    total_score = 0
    count = 0

    for item in news_items:
        s = 0.5
        try:
            if item.get('report_content'):
                s = SnowNLP(item['report_content']).sentiments
        except:
            pass
        total_score += s
        count += 1
        item['sentiment'] = s

    if count == 0:
        return 0
    
    avg_raw_score = total_score / count
    return (avg_raw_score - 0.5) * 2

async def fetch_and_cache_news():
    try:
        news_items = await asyncio.to_thread(_fetch_news_data_sync)
        if news_items:
            # [关键] 第一次更新缓存：有新闻，但情绪是 None
            # 前端看到这个，就会显示新闻列表 + "正在分析..."
            cached_data['news'] = {
                "items": news_items, 
                "sentiment_index": None 
            }
            print(f"--- [新闻任务] 阶段1完成: 已缓存 {len(news_items)} 条新闻 (等待分析) ---")
            
            # 2. 执行 NLP 分析
            sentiment_index = await asyncio.to_thread(_analyze_sentiment_sync, news_items)
            
            # [关键] 第二次更新缓存：补全情绪分数
            cached_data['news'] = {
                "items": news_items,
                "sentiment_index": sentiment_index
            }
            print(f"--- [新闻任务] 阶段2完成: 情绪指数 {sentiment_index:.2f} ---")

    except Exception as e:
        print(f"--- !!! [新闻任务] 失败 !!! ---\n错误: {e}")
        # 保持缓存现状，或者设为空
        if 'news' not in cached_data:
             cached_data['news'] = {"items": [], "sentiment_index": 0}

async def update_news_cache_periodically():
    while True:
        await asyncio.sleep(15 * 60) 
        print("--- [定时任务] 正在刷新新闻缓存... ---")
        await fetch_and_cache_news()