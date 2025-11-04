#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
report_generator.py
报告生成：将最新OHLCV + 指标结果汇总为结构化报告
职责：
  1. 生成结构化报告
  2. 压缩历史数据
  3. 构建AI提示词（Toon格式和人类可读格式）
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime, timedelta
import math
import json  # 新增: 用于 JSON 格式化输出
from job.indicator_calculator import SignalEntity

class ReportGenerator:
    def __init__(self):
        print("✅ ReportGenerator 初始化完成")

    def _generate_from_signal(self, signal_entity: SignalEntity) -> Dict[str, Any]:
        """直接从SignalEntity生成结构化报告，信号自适应"""
        meta = {
            'stock_code': signal_entity.stock_code,
            'stock_name': signal_entity.stock_name,
            'generate_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        price = signal_entity.price_info
        signals = signal_entity.signals
        # 动态提取所有激活信号
        positives = [k for k, v in signals.items() if v]
        summary = {
            'signal_count': len(positives),
            'active_signals': positives
        }
        report = {
            'meta': meta,
            'price': price,
            'signals': signals,
            'summary': summary
        }
        # 打印JSON
        print("=" * 80)
        print("✅ 生成报告(JSON):")
        try:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        except Exception:
            print(json.dumps(report, ensure_ascii=False, default=str, indent=2))
        return report

    def prepare_ai_data(self, signal_entity: SignalEntity, months: int = 6) -> Dict[str, Any]:
        """直接从SignalEntity准备AI数据，历史数据压缩自适应"""
        report = self._generate_from_signal(signal_entity)
        hist_df = signal_entity.history
        hist_info = self._compress_history(hist_df, months=months)
        prompt = self._build_toon_prompt(report, hist_info)
        human_prompt = self._build_human_prompt(report)
        print("=" * 80)
        print("可视化提示词" + human_prompt)
        system_prompt = self._build_system_prompt()
        return {
            'prompt': prompt,
            'system_prompt': system_prompt,
            'has_history': hist_info is not None,
            'hist_info': hist_info
        }

    # 历史序列压缩 -------------------------------------------------
    def _compress_history(self, hist_df: Optional[pd.DataFrame], months: int = 6,
                         col: str = '收盘', max_points: int = 120, include_dates: bool = True) -> Optional[Dict[str, Any]]:
        """压缩近N个月的收盘价序列为紧凑整数序列
        步骤：
          1. 按月份过滤最近N天数据
          2. 下采样至不超过max_points个点
          3. 用首值归一化(value/base*1000)并四舍五入为整数，便于减少token
          4. 计算统计指标：最小/最大/均值/标准差/总涨幅/年化波动近似
        Args:
            hist_df: 历史数据DataFrame（索引为日期）
            months: 向后追溯的月份数
            col: 使用的列名（默认'收盘'）
            max_points: 最大保留点数
        Returns:
            dict或None：包含压缩信息和统计；无数据时返回None
        """
        if hist_df is None or hist_df.empty or col not in hist_df.columns:
            return None
        if not isinstance(hist_df.index, pd.DatetimeIndex):
            try:
                hist_df.index = pd.to_datetime(hist_df.index)
            except Exception:
                pass
        cutoff = datetime.now() - timedelta(days=months*30)
        df = hist_df[hist_df.index >= cutoff]
        if df.empty:
            return None
        series = df[col].dropna()
        values = series.tolist()
        dates_full = df.index.tolist()
        n = len(values)
        stride = math.ceil(n / max_points) if n > max_points else 1
        sampled_values = values[::stride]
        sampled_dates = dates_full[::stride]
        base = sampled_values[0]
        if base == 0:
            base = next((v for v in sampled_values if v != 0), 1.0)
        norm_seq = [int(round(v / base * 1000)) for v in sampled_values]
        stats_min, stats_max = min(values), max(values)
        stats_mean = sum(values)/n
        stats_std = (sum((v-stats_mean)**2 for v in values)/(n-1))**0.5 if n>1 else 0.0
        stats_ret = (values[-1]/values[0]-1.0) if values[0]!=0 else 0.0
        annual_factor = 365/(months*30) if months>0 else 1
        stats_vol = stats_std/stats_mean*math.sqrt(annual_factor) if stats_mean!=0 else 0.0
        out = {
            'seq': ','.join(map(str, norm_seq)),
            'base': round(base, 4),
            'len': n,
            'stride': stride,
            'points': len(norm_seq),
            'min': round(stats_min, 4),
            'max': round(stats_max, 4),
            'ret': round(stats_ret, 4),
            'std': round(stats_std, 4),
            'vol': round(stats_vol, 4),
            'start_date': sampled_dates[0].strftime('%Y-%m-%d'),
            'end_date': sampled_dates[-1].strftime('%Y-%m-%d')
        }
        if include_dates:
            # 日期序列压缩：YYYYMMDD，无分隔，逗号分隔列表
            date_tokens = [d.strftime('%Y%m%d') for d in sampled_dates]
            out['dates'] = ','.join(date_tokens)
        return out

    # Toon 压缩提示词 -------------------------------------------------
    def _build_toon_prompt(self, report: Dict[str, Any], hist_info: Optional[Dict[str, Any]] = None) -> str:
        """生成 Toon 紧凑格式提示词（动态适配所有信号，无硬编码）
        结构：
            M: 基本信息 (代码/名称)
            P: 价格信息 (日期/开高低收/成交量)
            S: 技术信号(动态生成所有信号的键值对，值为1/0)
            SUM: 汇总(信号数/激活列表)
            TS: 历史统计 (len/pts/stride/base/ret/min/max/std/vol)
            SEQ: 压缩历史序列 (整数列表字符串)
        Args:
            report: 结构化报告
            hist_info: 由_compress_history返回的历史压缩信息
        Returns:
            str: Toon格式单行字符串
        """
        meta = report.get('meta', {})
        price = report.get('price', {})
        signals = report.get('signals', {})
        summary = report.get('summary', {})

        # 动态生成所有信号的键值对（按字母排序保证稳定性）
        signal_pairs = [f"{k}={1 if v else 0}" for k, v in sorted(signals.items())]
        signal_str = ','.join(signal_pairs) if signal_pairs else 'none'

        acts = summary.get('active_signals', [])
        act_str = ','.join(acts) if acts else 'none'

        toon = (f"M:c={meta.get('stock_code','')},n={meta.get('stock_name','')}"
                f";P:d={price.get('date','')},o={price.get('open',0):.2f},h={price.get('high',0):.2f},"
                f"l={price.get('low',0):.2f},c={price.get('close',0):.2f},v={int(price.get('volume',0))}"
                f";S:{signal_str}" 
                f";SUM:cnt={summary.get('signal_count',0)},signals={act_str}")

        if hist_info:
            toon += (f";TS:len={hist_info['len']},pts={hist_info['points']},stride={hist_info['stride']},"
                    f"base={hist_info['base']},ret={hist_info['ret']},min={hist_info['min']},"
                    f"max={hist_info['max']},std={hist_info['std']},vol={hist_info['vol']}")
            # 加入日期映射段 DS（日期起止 + 步长 + 日期序列）
            if 'start_date' in hist_info and 'end_date' in hist_info:
                toon += (f";DS:s={hist_info['start_date']},e={hist_info['end_date']},stride={hist_info['stride']}")
            if 'dates' in hist_info:
                toon += (f";DATES:{hist_info['dates']}")
            toon += (f";SEQ:{hist_info['seq']}")

        return toon

    def _build_human_prompt(self, report: Dict[str, Any]) -> str:
        """生成人类可读格式提示词（动态适配所有信号）"""
        meta = report.get('meta', {})
        price = report.get('price', {})
        signals = report.get('signals', {})
        summary = report.get('summary', {})

        acts = summary.get('active_signals', [])
        acts_line = '激活信号: ' + (', '.join(acts) if acts else '无')

        lines = [
            f"股票代码: {meta.get('stock_code', '')}",
            f"股票名称: {meta.get('stock_name', '')}",
            f"日期: {price.get('date', '')}",
            f"开盘: {price.get('open', 0):.2f}, 最高: {price.get('high', 0):.2f}",
            f"最低: {price.get('low', 0):.2f}, 收盘: {price.get('close', 0):.2f}",
            f"成交量: {price.get('volume', 0):.0f}",
            f"\n技术信号:"
        ]

        # 动态遍历所有信号（按字母排序）
        for signal_name in sorted(signals.keys()):
            signal_value = signals[signal_name]
            lines.append(f"  {signal_name}: {'是' if signal_value else '否'}")

        lines.append(f"\n{acts_line}")

        return '\n'.join(lines)

    def _build_system_prompt(self) -> str:
        """生成系统提示词（压缩版，节省token）"""
        return (
            "量化交易分析助手。输入含meta/price/signals(动态信号字典)/summary/TS历史统计(可选)。\n"
            "任务:给出仓位建议,含决策(加仓/减仓/保持/观望)/比例/挂单区间/目标价/止损价/理由/风险/观察点。\n"
            "决策规则:无信号=>观望;单信号=>小幅加仓;多信号=>积极;ret近max或vol高=>减仓;SEQ快速拉升=>观望。\n"
            "价格参考:加仓=close*(0.985~0.995);减仓=close*(1.005~1.015);止损=close*0.95~0.97;目标=close*1.03~1.06。\n"
            "输出格式(中文,非JSON):\n"
            "决策:<选项>\n加减仓:<比例>\n挂单:<区间>\n目标:<值>\n止损:<值>\n理由:1...2...\n风险:<1-3条>\n观察:<1-3条>\n"
            "要求:基于数据,准确可验证,数值保留2位小数,缺历史或无信号需说明,客观语气。"
        )

__all__ = ['ReportGenerator']
