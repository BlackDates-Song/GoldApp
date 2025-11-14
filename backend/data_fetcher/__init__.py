# backend/data_fetcher/__init__.py

# 从各个模块中 "导出" 关键函数
# 这使得 app.py 可以继续使用 data_fetcher.fetch_... 和 data_fetcher.update_...

from .kline import fetch_and_cache_k_lines

from .news import fetch_and_cache_news, update_news_cache_periodically

from .intraday import update_intraday_cache, intraday_cache_loop

from .global_markets import fetch_and_cache_global_markets, update_global_markets_periodically

from .domestic_macro import fetch_and_cache_domestic_macro, update_domestic_macro_periodically