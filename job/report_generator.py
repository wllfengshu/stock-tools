#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
report_generator.py
报告生成：将最新OHLCV + 指标结果汇总为结构化报告
"""
from typing import Dict, Any, List
import pandas as pd
from datetime import datetime

# 建议压缩标签映射（与 Toon 压缩一致）
SUGGESTION_COMPRESS_TAGS = {
    '双金叉': 'DXC',
    '突破': 'TP',
    '少量试探': 'SLST',
    '继续观察': 'GJGC',
    '共振': 'GZ'
}

# 信号字段标准名称
SIGNAL_FIELDS = [
    'kdj_golden_cross',
    'macd_golden_cross',
    'rsi_oversold'
]

class ReportGenerator:
    def __init__(self):
        print("✅ ReportGenerator 初始化完成")

    def generate(self, stock_code: str, stock_name: str, ohlcv: pd.DataFrame, indicators: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        if ohlcv is None or ohlcv.empty:
            raise ValueError('无有效K线数据')
        latest = ohlcv.iloc[-1]
        report = {
            'meta': {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'generate_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'price': {
                'date': latest.get('日期') if '日期' in ohlcv.columns else ohlcv.index[-1].strftime('%Y-%m-%d'),
                'open': float(latest.get('开盘', 0)),
                'high': float(latest.get('最高', 0)),
                'low': float(latest.get('最低', 0)),
                'close': float(latest.get('收盘', 0)),
                'volume': float(latest.get('成交量', 0))
            },
            'signals': {}
        }
        # 使用类内部方法提取信号
        signals = self._extract_signals(indicators)
        report['signals'] = signals
        # 活跃信号列表
        positives = [k for k, v in signals.items() if v]
        # 统一生成建议
        suggestion = self._build_suggestion(positives)
        report['summary'] = {
            'signal_count': len(positives),
            'active_signals': positives,
            'suggestion': suggestion
        }
        print("=" * 80)
        print(f"✅ 生成报告: {report}")
        return report

    def _extract_signals(self, indicators: Dict[str, pd.DataFrame]) -> Dict[str, bool]:
        """从指标结果中提取标准化信号字典"""
        signals: Dict[str, bool] = {}
        kdj = indicators.get('KDJ')
        if kdj is not None and not kdj.empty and 'KDJ_GOLDEN_CROSS' in kdj.columns:
            signals['kdj_golden_cross'] = bool(kdj['KDJ_GOLDEN_CROSS'].iloc[-1])
        macd = indicators.get('MACD')
        if macd is not None and not macd.empty and 'MACD_GOLDEN_CROSS' in macd.columns:
            signals['macd_golden_cross'] = bool(macd['MACD_GOLDEN_CROSS'].iloc[-1])
        rsi = indicators.get('RSI')
        if rsi is not None and not rsi.empty and 'RSI_OVERSOLD' in rsi.columns:
            signals['rsi_oversold'] = bool(rsi['RSI_OVERSOLD'].iloc[-1])
        return signals

    def _build_suggestion(self, active_signal_keys: List[str]) -> str:
        """根据活跃信号列表生成中文建议文本"""
        if not active_signal_keys:
            return '暂无明显多头技术信号，继续观察。'
        has_kdj = 'kdj_golden_cross' in active_signal_keys
        has_macd = 'macd_golden_cross' in active_signal_keys
        has_rsi_oversold = 'rsi_oversold' in active_signal_keys
        base = '技术信号: ' + ', '.join(active_signal_keys)
        if has_kdj and has_macd:
            return base + ' —— 双金叉共振，可关注突破机会。'
        if has_kdj or has_macd:
            return base + '，建议少量试探。'
        if has_rsi_oversold:
            return base + '（超卖反弹观察）'
        return base + '（信号较弱，继续观察）'

__all__ = ['ReportGenerator']
