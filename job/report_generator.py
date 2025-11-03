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
        """生成结构化报告
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            ohlcv: OHLCV数据
            indicators: 指标字典
        Returns:
            结构化报告字典
        """
        if ohlcv is None or ohlcv.empty:
            raise ValueError('无有效K线数据')
        latest = ohlcv.iloc[-1]
        raw_date = latest.get('日期') if '日期' in ohlcv.columns else ohlcv.index[-1]
        if isinstance(raw_date, (datetime, pd.Timestamp)):
            date_str = raw_date.strftime('%Y-%m-%d')
        else:
            date_str = str(raw_date)
        report = {
            'meta': {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'generate_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'price': {
                'date': date_str,
                'open': float(latest.get('开盘', 0)),
                'high': float(latest.get('最高', 0)),
                'low': float(latest.get('最低', 0)),
                'close': float(latest.get('收盘', 0)),
                'volume': float(latest.get('成交量', 0))
            },
            'signals': {}
        }
        signals = self._extract_signals(indicators)
        report['signals'] = signals
        positives = [k for k, v in signals.items() if v]
        # summary 仅保留事实（数量/列表/各布尔状态），不含结论性文字
        report['summary'] = {
            'signal_count': len(positives),
            'active_signals': positives,
            'has_kdj_golden_cross': signals.get('kdj_golden_cross', False),
            'has_macd_golden_cross': signals.get('macd_golden_cross', False),
            'has_rsi_oversold': signals.get('rsi_oversold', False)
        }
        # 使用 JSON 格式打印
        print("=" * 80)
        print("✅ 生成报告(JSON):")
        try:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        except Exception:
            # 兜底: 避免无法序列化异常中断
            print(json.dumps(report, ensure_ascii=False, default=str, indent=2))
        return report

    def prepare_ai_data(self, report: Dict[str, Any], hist_df: Optional[pd.DataFrame] = None,
                       months: int = 6, use_toon: bool = True) -> Dict[str, Any]:
        """准备AI所需的所有数据
        职责：
          1. 压缩历史数据
          2. 构建提示词（Toon或人类可读格式）
          3. 构建系统提示词
        Args:
            report: 结构化报告
            hist_df: 历史价格DataFrame
            months: 压缩历史的月份区间
            use_toon: True使用紧凑Toon格式，False使用人类可读格式
        Returns:
            包含prompt、system_prompt、has_history等的字典
        """
        # 压缩历史数据
        hist_info = self._compress_history(hist_df, months=months) if (use_toon and hist_df is not None) else None

        # 构建提示词
        if use_toon:
            prompt = self._build_toon_prompt(report, hist_info)
        else:
            prompt = self._build_human_prompt(report)

        # 构建系统提示词
        system_prompt = self._build_system_prompt()

        return {
            'prompt': prompt,
            'system_prompt': system_prompt,
            'has_history': hist_info is not None,
            'hist_info': hist_info
        }

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
            return base + ' ——双金叉共振，可关注突破机会。'
        if has_kdj or has_macd:
            return base + '，建议少量试探。'
        if has_rsi_oversold:
            return base + '（超卖反弹警惕）'
        return base + '（信号较弱，继续观察）'

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
        """生成 Toon 紧凑格式提示词
        结构：
            M: 基本信息 (代码/名称)
            P: 价格信息 (日期/开高低收/成交量)
            S: 技术信号(kdj, macd, rsi => 1/0)
            SUM: 汇总(信号数/激活列表/压缩建议)
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

        kdj = 1 if signals.get('kdj_golden_cross') else 0
        macd = 1 if signals.get('macd_golden_cross') else 0
        rsi = 1 if signals.get('rsi_oversold') else 0

        acts = summary.get('active_signals', [])
        act_str = ','.join(acts) if acts else ''

        # 事实描述：不做策略性建议，仅罗列信号
        facts = f"signals={act_str}" if act_str else "signals=none"

        toon = (f"M:c={meta.get('stock_code','')},n={meta.get('stock_name','')}"
                f";P:d={price.get('date','')},o={price.get('open',0):.2f},h={price.get('high',0):.2f},"
                f"l={price.get('low',0):.2f},c={price.get('close',0):.2f},v={int(price.get('volume',0))}"
                f";S:kdj={kdj},macd={macd},rsi={rsi}" 
                f";SUM:cnt={summary.get('signal_count',0)},{facts}")

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
        """生成人类可读格式提示词"""
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
            f"\n技术信号:",
            f"  KDJ金叉: {'是' if signals.get('kdj_golden_cross') else '否'}",
            f"  MACD金叉: {'是' if signals.get('macd_golden_cross') else '否'}",
            f"  RSI超卖: {'是' if signals.get('rsi_oversold') else '否'}",
            f"\n{acts_line}"
        ]

        return '\n'.join(lines)

    def _build_system_prompt(self) -> str:
        """生成系统提示词——指导模型输出加/减仓、挂单价格与理由的自然语言建议（不再要求 JSON）。"""
        return (
            "你是一名严格的数据驱动的量化交易分析助手。你收到的用户 prompt 中可能包含:"
            "1) meta: 股票代码/名称/生成时间"
            "2) price: 最新日价 (date/open/high/low/close/volume)"
            "3) signals: kdj_golden_cross / macd_golden_cross / rsi_oversold 布尔值"
            "4) summary: signal_count / active_signals / has_kdj_golden_cross / has_macd_golden_cross / has_rsi_oversold"
            "5) 历史压缩段(可选): TS(len,points,stride,base,ret,min,max,std,vol) + DS + DATES + SEQ (归一化整数序列)"
            "任务: 基于这些数据给出当前的仓位操作建议，包括:"
            "- 决策: 加仓 / 减仓 / 保持 / 观望"
            "- 加/减仓数量或比例建议: 可用资金百分比或现有仓位调整百分比 (示例: 加仓 30% / 减仓 20%)"
            "- 挂单价格区间: 给出分批买入或卖出区间 (基于当前 close 及近期波动, 示例: 买入区间 13.80~13.95)"
            "- 目标价与止损价: 目标价(例如 close 上方某合理百分比), 止损价(近期低点或 close 下方百分比)"
            "- 理由: 列出基于信号/波动/收益率(ret)/波动率(vol)/历史极值(min/max) 的客观逻辑"
            "- 风险提示: 可能的失效条件 (如金叉消失 / 波动扩大 / 涨幅透支)"
            "- 后续观察要点: 例如 成交量变化 / 二次金叉确认 / RSI 状态 / 政策新闻 (若未来出现)"
            "决策选择指引(仅示例, 需结合真实数据):"
            "- signal_count = 0 且无金叉 => 观望"
            "- 仅出现单一金叉 (KDJ 或 MACD) => 小幅加仓 或 保持 (结合波动率)"
            "- 同时 KDJ 与 MACD 金叉 => 偏积极, 可考虑加仓"
            "- RSI 超卖单独出现 => 可能反弹, 不盲目重仓"
            "- ret 接近历史 max 或 vol/std 显著升高 => 减仓或保持, 谨慎追高"
            "- SEQ 最近快速拉升且波动放大 => 保持/观望"
            "挂单价格区间参考规则(供你生成合理区间, 不要机械照抄文字):"
            "- 加仓: 以 close 为锚, 给出略低于 close 的分批吸筹区间 (如 close*(1 - 0.5%~1.5%))"
            "- 减仓: 以 close 或近期高点为锚, 给出卖出区间 (如 close*(1 + 0.5%~1.5%))"
            "- 观望/保持: 不给区间或仅提示条件触发价位"
            "- 止损价: 可参考近期低点或 close*(1 - 3%~5%)"
            "- 目标价: 可参考近阶段阻力位或 close*(1 + 3%~6%)，避免过度乐观"
            "输出格式要求(纯中文自然语言, 不要 JSON, 不要前缀解释, 结构清晰):"
            "决策: <加仓/减仓/保持/观望>"
            "加减仓建议: <分批或一次性 + 比例/数量说明>"
            "挂单价格: <买入区间 或 卖出区间>"
            "目标价: <数值或区间>"
            "止损价: <数值或区间>"
            "理由:  1. ...  2. ..."
            "风险: <列出1-3条>"
            "后续观察: <列出1-3条>"
            "注意事项:"
            "- 提供的建议必须基于输入数据和信号, 避免主观臆断。"
            "- 必须要准确、可验证，严禁编造数据。"
            "- 数值可用接近值(保留2位小数), 来源必须是现有字段推导。"
            "- 若缺少历史(无 has_history 或 SEQ 点数<20) => 明确说明数据不足并降低加仓建议。"
            "- 若全部信号为 False => 不可直接建议加仓, 需说明原因。"
            "- 用客观语气, 避免夸张词汇和感叹号, 不输出 JSON。"
            "- 没有止损逻辑时必须给出默认防守价位。"
            "现在请基于输入数据生成上述结构的建议。"
        )

__all__ = ['ReportGenerator']
