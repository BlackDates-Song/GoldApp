import asyncio
from contextlib import asynccontextmanager
import data_fetcher

@asynccontextmanager
async def lifespan(app):
    print("服务器启动...")

    # 1. 定义所有 *初始* 加载任务
    task_k_lines = asyncio.create_task(data_fetcher.fetch_and_cache_k_lines())
    task_news = asyncio.create_task(data_fetcher.fetch_and_cache_news())
    task_intraday = asyncio.create_task(data_fetcher.update_intraday_cache())
    task_global = asyncio.create_task(data_fetcher.fetch_and_cache_global_markets())
    task_domestic_macro = asyncio.create_task(data_fetcher.fetch_and_cache_domestic_macro())

    # 2. (v4.32 关键) *并行* 运行所有初始任务
    print("--- [启动] 正在并行加载所有初始数据 (K线, 新闻, 分时图, 宏观)... ---")
    await asyncio.gather(
        task_k_lines,
        task_news,
        task_intraday,
        task_global,
        task_domestic_macro
    )
    print("--- [启动] 所有初始数据加载完毕! 服务器准备就绪。 ---")

    # 3. (v4.32 关键) *在所有数据都绪后*，再启动后台的 *定时刷新* 任务
    asyncio.create_task(data_fetcher.update_news_cache_periodically())
    asyncio.create_task(data_fetcher.intraday_cache_loop())
    asyncio.create_task(data_fetcher.update_global_markets_periodically())
    asyncio.create_task(data_fetcher.update_domestic_macro_periodically())
    
    print("--- [启动] 所有后台定时刷新任务已启动 ---")
        
    yield
    print("服务器关闭。")