#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
indicator_calculator.py
技术指标计算模块：KDJ / MACD / RSI
统一接口：IndicatorCalculator.calculate_indicators(df, custom_params)
输入要求：DataFrame 需包含列 ['最高','最低','收盘']
扩展方式：新增 calc_xxx 方法并在 calculate_indicators 中注册即可。

学习提示：
1. 技术指标都是基于历史价格的数学变换，用来描述当前行情的状态（超买/超卖、趋势强度、转折等）。
2. 指标本身不保证盈利，只是辅助决策；可以与成交量、形态、基本面结合。
3. 这里的实现都使用 pandas 的滚动窗口和指数移动平均（EMA）。
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np
from job.config import INDICATOR_DEFAULTS

class SignalEntity:
    """通用技术指标信号实体类，支持扩展和无感适配"""
    def __init__(self, stock_code: str, stock_name: str, price_info: dict, signals: dict, history: pd.DataFrame = None, extra: dict = None):
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.price_info = price_info  # {'date':..., 'open':..., ...}
        self.signals = signals        # {'kdj_golden_cross': True, ...}
        self.history = history        # 原始或压缩历史数据
        self.extra = extra or {}      # 其他扩展字段（如新闻、政策等）

    def get_signal(self, key):
        return self.signals.get(key, None)

    def to_dict(self):
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'price_info': self.price_info,
            'signals': self.signals,
            'history': self.history,
            'extra': self.extra
        }


class IndicatorCalculator:
    """技术指标计算器

    使用方式：
        calc = IndicatorCalculator()
        result_dict = calc.calculate_indicators(df)
        # result_dict['KDJ'], result_dict['MACD'], result_dict['RSI'] 为各指标的 DataFrame

    设计要点：
    - 每个 calc_XXX 方法只负责单一指标的计算，保持简单易维护。
    - calculate_indicators 汇总调用，方便一次性得到全部结果。
    - 支持传入 custom_params 覆盖默认参数（例如修改 MACD 的 fast/slow 周期）。
    """
    def __init__(self):
        print("✅ IndicatorCalculator 初始化完成")

    def _calc_kdj(self, df: pd.DataFrame, n: int = 9, k_smooth: int = 3, d_smooth: int = 3) -> pd.DataFrame:
        """计算 KDJ 指标
        KDJ 是从 RSV(未成熟随机值) 平滑得到的 K、D，再计算 J = 3K - 2D。
        应用场景：
            - K 与 D 发生金叉 (K 上穿 D) 常被认为是短线买入信号。
            - J 极端高/低可能提示价格即将回调。
        参数说明：
            n: 计算 RSV 时的周期长度(默认9)。
            k_smooth: K 线的平滑参数 (相当于几周期指数平均)。
            d_smooth: D 线的平滑参数。
        返回：DataFrame 包含列 ['K','D','J','KDJ_GOLDEN_CROSS']
        计算步骤：
            1) 找到最近 n 日的最高价 high_max 与最低价 low_min。
            2) RSV = (收盘价 - low_min) / (high_max - low_min) * 100。
            3) K = 对 RSV 做指数加权平均；D = 对 K 再做指数加权平均。
            4) J = 3K - 2D，提供更敏感的波动反应。
            5) 金叉判断：当前 K > D 且昨天 K <= D。
        注意：若区间无波动 (high_max == low_min) 会导致除零，pandas 会产生 NaN；后续平滑会自动处理。
        """
        # 取需要的列
        high = df['最高']
        low = df['最低']
        close = df['收盘']
        # 最近 n 日最低与最高
        low_min = low.rolling(n).min()
        high_max = high.rolling(n).max()
        # RSV 原始随机指标
        rsv = (close - low_min) / (high_max - low_min) * 100
        # K / D 采用指数加权移动平均 (EMA) 进行平滑
        k = rsv.ewm(com=k_smooth - 1, adjust=False).mean()
        d = k.ewm(com=d_smooth - 1, adjust=False).mean()
        # J 的放大公式（更敏感）
        j = 3 * k - 2 * d
        out = pd.DataFrame({'K': k, 'D': d, 'J': j})
        # 金叉状态：K在D上方（持续状态，选股工具通常指这个）
        out['KDJ_GOLDEN_CROSS'] = out['K'] > out['D']
        # 金叉事件：K今天上穿D（刚发生的事件）
        out['KDJ_GOLDEN_CROSS_EVENT'] = (out['K'] > out['D']) & (out['K'].shift(1) <= out['D'].shift(1))
        return out

    def _calc_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """计算 MACD 指标
        MACD 核心：快线 DIF = EMA(fast) - EMA(slow)，慢线 DEA = DIF 的 EMA(signal)，柱状图 MACD = (DIF - DEA)*2。
        应用场景：
            - DIF 上穿 DEA 称为“金叉”，常作为趋势反转或强化的信号。
            - 柱状图由负转正，动能可能由空方转向多方。
        参数：
            fast: 快均线周期 (默认12)
            slow: 慢均线周期 (默认26)
            signal: DEA 平滑周期 (默认9)
        返回：DataFrame 包含 ['DIF','DEA','MACD','MACD_GOLDEN_CROSS']
        计算步骤：
            1) 计算收盘价的快/慢指数移动平均 (EMA)。
            2) DIF = EMA_fast - EMA_slow。
            3) DEA = DIF 的 EMA(signal)。
            4) 柱状 MACD = (DIF - DEA) * 2。
            5) 金叉：当前 DIF > DEA 且前一日 DIF <= DEA。
        注意：EMA 使用 adjust=False，保持传统技术分析实现方式。
        """
        close = df['收盘']
        # 快/慢 EMA
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        # DIF 差值
        dif = ema_fast - ema_slow
        # DEA 对 DIF 再平滑
        dea = dif.ewm(span=signal, adjust=False).mean()
        # 柱状图放大 (常规 *2 用于直观显示力度)
        macd = (dif - dea) * 2
        out = pd.DataFrame({'DIF': dif, 'DEA': dea, 'MACD': macd})
        # 金叉状态：DIF在DEA上方（持续状态，选股工具通常指这个）
        out['MACD_GOLDEN_CROSS'] = out['DIF'] > out['DEA']
        # 金叉事件：DIF今天上穿DEA（刚发生的事件）
        out['MACD_GOLDEN_CROSS_EVENT'] = (out['DIF'] > out['DEA']) & (out['DIF'].shift(1) <= out['DEA'].shift(1))
        return out

    def _calc_rsi(self, df: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        """计算 RSI 指标
        RSI(相对强弱指数) 衡量一段时间内上涨幅度与下跌幅度的比值，反映动能强弱。
        简化公式：RSI = 100 - 100 / (1 + RS)，其中 RS = 平均上涨 / 平均下跌。
        应用场景：
            - RSI 很低（如 <20）可能是超卖，价格有反弹机会。
            - RSI 很高（如 >80）可能是超买，价格有回调风险。
        参数：
            periods: 需要计算的多个周期列表，例如 [6,12,24]。
        返回：包含各周期 RSI 列，如 'RSI_6','RSI_12',... 以及一个简易超卖标记 'RSI_OVERSOLD' (仅基于 RSI_6 < 20)。
        计算步骤：
            1) 价格差分 delta = 当日收盘 - 昨日收盘。
            2) gain = 正差分 (上涨部分)，loss = 负差分的绝对值 (下跌力度)。
            3) 对每个周期 p：求 gain 与 loss 的滚动平均，RS = avg_gain / avg_loss。
            4) RSI = 100 - 100/(1+RS)。
        注意：loss 为 0 会导致 RS 无穷大，这里通过 replace(0, np.nan) 避免除零，使 RSI 贴近 100。
        """
        close = df['收盘']
        # 差分（第一行没有前一天值，会是 NaN）
        delta = close.diff()
        # 上涨部分：负值裁剪为0；下跌部分：正值裁剪为0后取负号得到正的下跌幅度
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        out = pd.DataFrame(index=df.index)
        for p in periods:
            # 滚动平均（简单平均，可根据需要换成指数平均）
            avg_gain = gain.rolling(p).mean()
            avg_loss = loss.rolling(p).mean()
            rs = avg_gain / (avg_loss.replace(0, np.nan))
            rsi = 100 - 100 / (1 + rs)
            out[f'RSI_{p}'] = rsi.fillna(0)  # 前期不足 p 天的用 0 填充
        # 简单超卖标记（可扩展成更复杂规则）
        if 'RSI_6' in out.columns:
            out['RSI_OVERSOLD'] = out['RSI_6'] < 20
        return out

    def calculate_signals(self, stock_code: str, stock_name: str, df: pd.DataFrame, custom_params: Dict[str, Any] = None, history: pd.DataFrame = None, extra: dict = None) -> SignalEntity:
        """统一计算所有信号并返回SignalEntity"""
        if df is None or df.empty:
            raise ValueError('输入DataFrame为空')
        required = {'最高', '最低', '收盘'}
        if not required.issubset(df.columns):
            raise ValueError(f'缺少必要列: {required - set(df.columns)}')
        params = {k: v.copy() for k, v in INDICATOR_DEFAULTS.items()}
        if custom_params:
            for k, v in custom_params.items():
                if k in params and isinstance(v, dict):
                    params[k].update(v)
        # 计算所有指标
        kdj = self._calc_kdj(df, **params['KDJ'])
        macd = self._calc_macd(df, **params['MACD'])
        rsi = self._calc_rsi(df, periods=params['RSI']['periods'])
        # 最新价格信息
        latest = df.iloc[-1]
        price_info = {
            'date': str(latest.get('日期', df.index[-1]) if '日期' in df.columns else df.index[-1]),
            'open': float(latest.get('开盘', 0)),
            'high': float(latest.get('最高', 0)),
            'low': float(latest.get('最低', 0)),
            'close': float(latest.get('收盘', 0)),
            'volume': float(latest.get('成交量', 0))
        }
        # 动态收集所有信号
        signals = {}
        if not kdj.empty and 'KDJ_GOLDEN_CROSS' in kdj.columns:
            signals['kdj_golden_cross'] = bool(kdj['KDJ_GOLDEN_CROSS'].iloc[-1])
        if not macd.empty and 'MACD_GOLDEN_CROSS' in macd.columns:
            signals['macd_golden_cross'] = bool(macd['MACD_GOLDEN_CROSS'].iloc[-1])
        if not rsi.empty and 'RSI_OVERSOLD' in rsi.columns:
            signals['rsi_oversold'] = bool(rsi['RSI_OVERSOLD'].iloc[-1])
        # 可扩展：自动收集所有以 _CROSS/_SIGNAL/_ALERT/_OVERSOLD/_OVERBOUGHT 结尾的布尔信号
        for df_ind in [kdj, macd, rsi]:
            for col in df_ind.columns:
                if col.endswith(('_CROSS', '_SIGNAL', '_ALERT', '_OVERSOLD', '_OVERBOUGHT')) and col.lower() not in signals:
                    val = df_ind[col].iloc[-1]
                    if isinstance(val, (bool, np.bool_)) or (isinstance(val, (int, float)) and val in (0, 1)):
                        signals[col.lower()] = bool(val)
        return SignalEntity(stock_code, stock_name, price_info, signals, history=history, extra=extra)

__all__ = ["IndicatorCalculator"]
