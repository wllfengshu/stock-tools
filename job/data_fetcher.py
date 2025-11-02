#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
data_fetcher.py
数据获取：封装 AKShare 接口，统一标准 OHLCV 输出

模块职责：
1. 提供股票与伦敦金历史数据获取接口（带简单重试）
2. 标准化字段名为统一的中文列名：开盘 / 最高 / 最低 / 收盘 / 成交量
3. 提供一个简单的“实时价格”占位方法（实际用最近收盘价代替）
"""

from typing import Optional
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time, random

class DataFetcher:
    def __init__(self, retry: int = 2, retry_sleep: float = 1.0):
        """构造函数
        Args:
            retry: 每个接口最大重试次数（失败后再尝试次数，不含首次）
            retry_sleep: 每次重试的基础休眠秒数（会再加一个随机抖动）
        说明：重试是简单线性策略，可后续改成指数退避。
        """
        self.retry = retry
        self.retry_sleep = retry_sleep
        print("✅ DataFetcher 初始化完成 (retry=%d, retry_sleep=%.2f)" % (retry, retry_sleep))

    def _standardize(self, df: pd.DataFrame) -> pd.DataFrame:
        """内部工具：标准化原始数据格式
        处理步骤：
        1. 统一日期索引为 DatetimeIndex；若存在 '日期' 列则设为索引
        2. 将可能出现的英文列名映射为标准中文列名：开盘/最高/最低/收盘/成交量
        3. 排序索引确保时间正序
        Args:
            df: 原始 DataFrame
        Returns:
            标准化后的 DataFrame；若输入为空则返回空 DataFrame
        """
        if df is None or df.empty:
            return pd.DataFrame()
        # 统一日期索引
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.set_index('日期', drop=False)
        elif not isinstance(df.index, pd.DatetimeIndex):  # 若索引不是日期尝试转换
            try:
                df.index = pd.to_datetime(df.index)
            except Exception:
                pass
        # 英文列名 -> 中文列名映射
        mapping = {
            'open': '开盘','high':'最高','low':'最低','close':'收盘','volume':'成交量',
            'Open':'开盘','High':'最高','Low':'最低','Close':'收盘','Volume':'成交量'
        }
        for src, dst in mapping.items():
            if src in df.columns and dst not in df.columns:
                df[dst] = df[src]
        return df.sort_index()

    def fetch_stock_hist(self, code: str, months: int = 12) -> pd.DataFrame:
        """获取 A 股股票历史日线（前复权）
        Args:
            code: 股票代码（例如 '002155'）
            months: 向前抓取的月数（按 30 天近似换算）
        Returns:
            标准化后的日线 DataFrame（包含至少收盘价等列）
        Raises:
            RuntimeError: 重试后仍失败时抛出异常
        注意：
            - 使用 akshare.stock_zh_a_hist 接口，adjust='qfq'（前复权）
            - 若后续需要后复权或不复权，可增加参数支持
        """
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=months*30)).strftime('%Y%m%d')
        last_err = None
        for attempt in range(self.retry + 1):
            try:
                df = ak.stock_zh_a_hist(symbol=code, period='daily', start_date=start, end_date=end, adjust='qfq')
                return self._standardize(df)
            except Exception as e:
                last_err = e
                # 重试前休眠（基础秒数 + 随机抖动）
                time.sleep(self.retry_sleep + random.random())
        # 所有尝试失败
        raise RuntimeError(f'获取股票{code}失败: {last_err}')

    def fetch_gold_hist(self, months: int = 12) -> pd.DataFrame:
        """获取伦敦金（XAU）历史数据
        Args:
            months: 向前抓取的月数
        Returns:
            标准化后的伦敦金日线 DataFrame
        Raises:
            RuntimeError: 重试后仍失败
        备注：接口 ak.futures_foreign_hist(symbol='XAU') 返回的字段可能包含英文列，这里做统一映射。
        """
        last_err = None
        for attempt in range(self.retry + 1):
            try:
                df = ak.futures_foreign_hist(symbol='XAU')
                df = self._standardize(df)
                cutoff = datetime.now() - timedelta(days=months*30)
                df = df[df.index >= cutoff]
                return df
            except Exception as e:
                last_err = e
                time.sleep(self.retry_sleep + random.random())
        raise RuntimeError(f'获取伦敦金失败: {last_err}')

    def fetch_realtime_quote(self, code: str) -> Optional[float]:
        """获取“实时”价格（占位实现）
        当前实现：用最近一次日线收盘价代替实时价，避免接入复杂的行情源。
        Args:
            code: 股票代码
        Returns:
            最近一条收盘价（float）；若失败或无数据返回 None
        后续扩展：可接入 websocket / level2 / 行情轮询接口。
        """
        try:
            df = self.fetch_stock_hist(code, months=1)
            if not df.empty:
                return float(df['收盘'].iloc[-1])
        except Exception:
            return None
        return None

__all__ = ['DataFetcher']
