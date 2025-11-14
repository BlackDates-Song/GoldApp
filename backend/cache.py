from typing import Any, Dict

# --- 1. 缓存 (用于K线, 新闻, 和 各种数据) ---
cached_data: Dict[str, Any] = {}

# --- (v4.29) 专用于分时图的精细化缓存 ---
intraday_cache = {
    "night_session": [],
    "day_session": [],
    "last_trade_date_str": None
}