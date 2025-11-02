#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
配置模块
提供：
1. 股票列表（可按板块分组）
2. 全局运行参数（抓取周期、默认时间范围等）
3. 指标参数默认值（支持后期扩展）

扩展方式：
- 新增板块只需在 SECTORS / STOCK_POOLS 中添加
- 新增指标默认参数在 INDICATOR_DEFAULTS 中添加
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

# 黄金&有色板块股票列表（仅示例，可随时扩展/替换）
GOLD_STOCKS: List[Dict[str, str]] = [
    {"code": "002155", "name": "湖南黄金", "sector": "黄金开采"},
    # {"code": "600547", "name": "山东黄金", "sector": "黄金开采"},
    # {"code": "000975", "name": "银泰黄金", "sector": "黄金开采"},
    # {"code": "600489", "name": "中金黄金", "sector": "黄金开采"},
    # {"code": "002237", "name": "恒邦股份", "sector": "黄金冶炼"},
    # {"code": "600988", "name": "赤峰黄金", "sector": "黄金开采"},
    # {"code": "600311", "name": "荣华实业", "sector": "黄金开采"},
    # {"code": "000060", "name": "中金岭南", "sector": "有色金属"},
    # {"code": "600362", "name": "江西铜业", "sector": "有色金属"},
    # {"code": "000630", "name": "铜陵有色", "sector": "有色金属"}
]

SECTORS = {
    "黄金开采": [s for s in GOLD_STOCKS if s["sector"] == "黄金开采"],
    "黄金冶炼": [s for s in GOLD_STOCKS if s["sector"] == "黄金冶炼"],
    "有色金属": [s for s in GOLD_STOCKS if s["sector"] == "有色金属"],
}

STOCK_POOLS = {
    "default": GOLD_STOCKS,
    "gold": SECTORS["黄金开采"],
    "nonferrous": SECTORS["有色金属"],
}

INDICATOR_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "KDJ": {"n": 9, "k_smooth": 3, "d_smooth": 3},
    "MACD": {"fast": 12, "slow": 26, "signal": 9},
    "RSI": {"periods": [6, 12, 24]},
}

@dataclass
class RuntimeConfig:
    months: int = 12  # 默认抓取近12个月
    enable_realtime: bool = True
    schedule_times: List[str] = field(default_factory=lambda: ["09:00", "14:30"])  # 每日执行时间
    ai_enabled: bool = False
    message_push_enabled: bool = False
    stock_pool: str = "default"

    def get_stock_list(self) -> List[Dict[str, str]]:
        return STOCK_POOLS.get(self.stock_pool, GOLD_STOCKS)

GLOBAL_CONFIG = RuntimeConfig()

__all__ = [
    "GOLD_STOCKS", "SECTORS", "STOCK_POOLS", "INDICATOR_DEFAULTS", "RuntimeConfig", "GLOBAL_CONFIG"
]

