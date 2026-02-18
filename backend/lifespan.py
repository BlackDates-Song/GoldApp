import asyncio
from contextlib import asynccontextmanager
import data_fetcher # 这是一个包
import traceback # [v4.69] 导入 traceback
import gc

from utils import log_memory

@asynccontextmanager
async def lifespan(app):
    print("--- 服务器启动... ---")
    log_memory("启动开始")
    
    try:
        log_memory("核心任务开始")
        # 1. 定义所有 *初始* 加载任务
        core_tasks = [
            asyncio.create_task(data_fetcher.fetch_and_cache_k_lines()),
            asyncio.create_task(data_fetcher.update_intraday_cache()),
            asyncio.create_task(data_fetcher.fetch_and_cache_global_markets()),
            asyncio.create_task(data_fetcher.fetch_and_cache_domestic_macro()),
            asyncio.create_task(data_fetcher.fetch_and_cache_market_indicators()),
        ]

        # 2. *并行* 运行所有初始任务
        print(f"--- [启动] 正在并行加载 {len(core_tasks)} 个初始数据任务... ---")
        await asyncio.gather(*core_tasks)  # [v4.69] 正确地解包 core_tasks 列表
        
        print("--- [启动] 核心任务加载完毕! ---")
        gc.collect()  # [v4.69] 强制进行垃圾回收，释放内存
        log_memory("核心任务结束")

    except Exception as e:
        # [v4.69] 关键: 捕获并打印启动期间的任何错误
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"--- [启动] 致命错误: 启动核心任务失败! ---")
        print(f"--- 错误: {e} ---")
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # 即使启动失败，也要 yield，以便服务器至少能运行并返回错误

    print(f"--- [启动] 正在启动后台定时刷新任务... ---")
    asyncio.create_task(data_fetcher.intraday_cache_loop())
    asyncio.create_task(data_fetcher.update_global_markets_periodically())
    asyncio.create_task(data_fetcher.update_domestic_macro_periodically())
    asyncio.create_task(data_fetcher.update_market_indicators_periodically())
    asyncio.create_task(data_fetcher.update_spdr_gold_periodically())
    print("--- [启动] 所有后台定时刷新任务已启动 ---")

    print("--- [启动] 正在启动新闻加载任务 ---")
    log_memory("新闻任务开始")
    asyncio.create_task(data_fetcher.fetch_and_cache_news())
    asyncio.create_task(data_fetcher.update_news_cache_periodically())
    print("--- [启动] 新闻加载任务已启动 ---")
    log_memory("新闻任务结束")

    print("--- [启动] 正在启动慢速SPDR任务 ---")
    log_memory("慢速SPDR任务开始")
    asyncio.create_task(data_fetcher.fetch_and_cache_spdr_gold())
    asyncio.create_task(data_fetcher.update_spdr_gold_periodically())
    print("--- [启动] 慢速SPDR任务已启动 ---")
    log_memory("慢速SPDR任务结束")
    
    print("--- 全部任务启动完毕，服务器上线---")     
    yield
    print("--- 服务器关闭。---")