#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
黄金板块交易策略配置文件
"""

# ==================== 交易参数配置 ====================

# 基础交易参数
BASE_INVESTMENT = 10000  # 每次买入的基础金额（元）
TARGET_STOCK_CODE = "002155"  # 目标股票代码（湖南黄金）
TARGET_STOCK_NAME = "湖南黄金"  # 目标股票名称

# 交易时间参数
DATA_FETCH_TIME = "08:00"  # 数据获取时间（早上8点）
TRADING_START_TIME = "09:30"  # 交易开始时间（早上9:30）

# 止损止盈参数
STOP_LOSS_RATE = 0.10  # 止损比例（10%）
PROFIT_TAKE_RATE = 0.05  # 目标盈利比例（5%）
PROFIT_CALLBACK_RATE = 0.04  # 盈利回调卖出比例（4%）

# 数据源配置
GOLD_PRICE_SOURCE = "sina"  # 金价数据源
STOCK_DATA_SOURCE = "sina"  # 股票数据源

# 策略执行参数
STRATEGY_NAME = "黄金板块跟随策略"
VERSION = "1.0.0"

# ==================== 金价数据源配置 ====================

# 金价API配置（实际使用时需要配置真实API）
GOLD_API_CONFIG = {
    "sina": {
        "url": "https://hq.sinajs.cn/list=GC00Y",
        "description": "新浪财经金价数据"
    },
    "eastmoney": {
        "url": "https://quote.eastmoney.com/center/gridlist.html#hs_a_board",
        "description": "东方财富金价数据"
    }
}

# ==================== 股票数据源配置 ====================

STOCK_API_CONFIG = {
    "sina": {
        "description": "新浪财经股票数据"
    },
    "eastmoney": {
        "description": "东方财富股票数据"
    }
}

# ==================== 风险控制参数 ====================

# 最大持仓天数
MAX_HOLDING_DAYS = 5  # 最大持仓天数

# 最大单次投资金额
MAX_SINGLE_INVESTMENT = 50000  # 最大单次投资金额（元）

# 最大总持仓金额
MAX_TOTAL_POSITION = 200000  # 最大总持仓金额（元）

# ==================== 日志配置 ====================

LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "gold/strategy.log"
}

# ==================== 通知配置 ====================

NOTIFICATION_CONFIG = {
    "email": {
        "enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "",
        "password": ""
    },
    "wechat": {
        "enabled": False,
        "webhook_url": ""
    }
}
