import asyncio
from contextlib import asynccontextmanager
import data_fetcher # 这是一个包
import traceback # [v4.69] 导入 traceback

@asynccontextmanager
async def lifespan(app):
    print("--- 服务器启动... ---")
    
    try:
        # 1. 定义所有 *初始* 加载任务
        tasks = [
            asyncio.create_task(data_fetcher.fetch_and_cache_k_lines()),
            asyncio.create_task(data_fetcher.fetch_and_cache_news()),
            asyncio.create_task(data_fetcher.update_intraday_cache()),
            asyncio.create_task(data_fetcher.fetch_and_cache_global_markets()),
            asyncio.create_task(data_fetcher.fetch_and_cache_domestic_macro()),
            asyncio.create_task(data_fetcher.fetch_and_cache_market_indicators())
        ]

        # 2. *并行* 运行所有初始任务
        print(f"--- [启动] 正在并行加载 {len(tasks)} 个初始数据任务... ---")
        await asyncio.gather(*tasks)  # [v4.69] 正确地解包 tasks 列表
        
        print("--- [启动] 所有初始数据加载完毕! 服务器准备就绪。 ---")

        # 3. 启动后台的 *定时刷新* 任务
        asyncio.create_task(data_fetcher.update_news_cache_periodically())
        asyncio.create_task(data_fetcher.intraday_cache_loop())
        asyncio.create_task(data_fetcher.update_global_markets_periodically())
        asyncio.create_task(data_fetcher.update_domestic_macro_periodically())
        asyncio.create_task(data_fetcher.update_market_indicators_periodically())
        
        print("--- [启动] 所有后台定时刷新任务已启动 ---")
    
    except Exception as e:
        # [v4.69] 关键: 捕获并打印启动期间的任何错误
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"--- [启动] 致命错误: 启动任务失败! ---")
        print(f"--- 错误: {e} ---")
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # 即使启动失败，也要 yield，以便服务器至少能运行并返回错误
        
    yield
    
    print("--- 服务器关闭。---")