#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
ai_client.py
统一真实 AI 调用客户端
始终尝试调用远端模型接口；若缺少 token 返回错误信息。
"""
import os, time, json, math
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import requests

class AIClient:
    def __init__(self, api_url: Optional[str] = None, api_token: Optional[str] = None,
                 model: Optional[str] = None, timeout: float = 60.0, retries: int = 1):
        """构造函数
        Args:
            api_url: 覆盖默认接口地址，默认从环境变量 SILICONFLOW_API_URL 或常用地址。
            api_token: API访问密钥（建议通过环境变量 SILICONFLOW_API_TOKEN）。
            model: 使用的模型名称（例如 deepseek-ai/DeepSeek-V3），可通过 SILICONFLOW_MODEL 覆盖。
            timeout: 单次HTTP请求超时时间（秒）。
            retries: 失败后重试次数（不含首次）。
        安全说明：真实 token 不应写入代码，这里默认读取环境变量；若未提供真实 token 将在调用时给出错误提示。
        """
        # 真实调用所需配置
        self.api_url = api_url or os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.api_token = api_token or os.getenv('SILICONFLOW_API_TOKEN', 'sk-nypfpxrbfrlrtxbzczpkrgexpxjnaitxbubuojjhtcxgedjm')
        self.model = model or os.getenv('SILICONFLOW_MODEL', 'deepseek-ai/DeepSeek-V3')
        self.timeout = timeout
        self.retries = max(0, retries)
        print(f"✅ AIClient 初始化: model={self.model}, retries={self.retries}")

    def call(self, report: Dict[str, Any], hist_df: Optional[pd.DataFrame] = None, months: int = 6,
             use_toon: bool = True, use_ai: bool = True,
             temperature: float = 0.7, max_tokens: int = 1024) -> Dict[str, Any]:
        """统一调用入口（始终真实接口调用，若缺少 token 返回错误）
        流程：
          1. 根据结构化报告生成人类可读提示词 human_prompt。
          2. 可选：压缩近 months 月历史收盘价生成 Toon 格式（含 SEQ 序列）。
          3. 生成最终 prompt 并调用远端模型接口。
        Args:
            report: 由 ReportGenerator 生成的结构化报告字典。
            hist_df: 历史价格 DataFrame，用于生成压缩序列（可选）。
            months: 压缩历史的月份区间（默认6）。
            use_toon: True 使用紧凑 Toon 格式；False 使用人类可读格式。
            use_ai: True 执行真实模型调用；False 仅返回构造的 prompt。
            temperature: 采样温度（控制随机性）。
            max_tokens: 最大生成 token 数。
        Returns:
            dict：包含 prompt / ai_summary / has_history / error（若失败）等。
        """
        # 构造提示词
        hist_info = self._compress_history(hist_df, months=months) if (use_toon and hist_df is not None) else None
        prompt = self._build_toon_prompt(report, hist_info)
        system_prompt = self._build_system_prompt()
        result: Dict[str, Any] = {
            'prompt': prompt,
            'has_history': hist_info is not None,
            'model': self.model,
            'system_prompt': system_prompt
        }
        print("="*80)
        print(f"🚀 调用 AI 模型: {result}")
        # 缺少 token 时直接返回错误
        if not self.api_token:
            result['error'] = '缺少 API Token (SILICONFLOW_API_TOKEN)'
            return result
        payload = self._build_payload(system_prompt, prompt, temperature, max_tokens)
        if use_ai:
            api_response = self._request_api(payload)
            result.update(api_response)
        return result

    def _build_payload(self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> Dict[str, Any]:
        """构建硅基流动兼容的请求体
        Args:
            system_prompt: 系统级角色提示
            user_prompt: 用户主体内容（Toon 或人类可读）
            temperature: 随机性参数
            max_tokens: 最大生成 token 限制
        Returns:
            dict: 可直接序列化为 JSON 的请求体。
        """
        return {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': temperature,
            'max_tokens': max_tokens
        }

    def _request_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行真实 HTTP 请求调用模型服务
        具备：
          - 重试机制（线性退避）
          - 超时与异常捕获
        Args:
            payload: 已构建的请求体
        Returns:
            dict: 包含 ai_summary 或 error / details
        """
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                start = time.time()
                resp = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)
                elapsed = round(time.time() - start, 3)
                if resp.status_code >= 400:
                    return {'error': f'HTTP {resp.status_code}', 'details': resp.text[:500], 'latency': elapsed}
                data = resp.json()
                text = self._extract_text(data)
                return {'ai_summary': text, 'raw_response': data, 'latency': elapsed}
            except requests.exceptions.Timeout as e:
                last_error = f'Timeout: {e}'
            except requests.exceptions.RequestException as e:
                last_error = f'RequestException: {e}'
            except json.JSONDecodeError as e:
                last_error = f'JSONDecodeError: {e}'
            time.sleep(1.0 * (attempt + 1))
        return {'error': 'API调用失败', 'details': last_error, 'latency': None}

    def _extract_text(self, response: Dict[str, Any]) -> str:
        """从模型返回结构中提取文本
        兼容 OpenAI 风格：response['choices'][0]['message']['content']
        若结构异常或无内容，则返回部分原始 JSON 或错误信息。
        Args:
            response: 完整的接口返回字典
        Returns:
            str: 提取出的文本内容或占位说明
        """
        try:
            choices = response.get('choices') or []
            if not choices:
                return '[无choices返回]'
            msg = choices[0].get('message') or {}
            content = msg.get('content')
            return content.strip() if content else json.dumps(response)[:500]
        except Exception as e:
            return f'[解析失败] {e}'

    # 历史序列压缩 -------------------------------------------------
    def _compress_history(self, hist_df: Optional[pd.DataFrame], months: int = 6, col: str = '收盘', max_points: int = 120) -> Optional[Dict[str, Any]]:
        """压缩近 months 月的收盘价序列为紧凑整数序列
        步骤：
          1. 按月份过滤最近 N 天数据
          2. 下采样至不超过 max_points 个点
          3. 用首值归一化 (value/base*1000) 并四舍五入为整数，便于减少 token
          4. 计算统计指标：最小 / 最大 / 均值 / 标准差 / 总涨幅 / 年化波动近似
        Args:
            hist_df: 历史数据 DataFrame（索引为日期）
            months: 向后追溯的月份数
            col: 使用的列名（默认 '收盘'）
            max_points: 最大保留点数
        Returns:
            dict 或 None：包含压缩信息和统计；无数据时返回 None
        """
        if hist_df is None or hist_df.empty or col not in hist_df.columns:
            return None
        if not isinstance(hist_df.index, pd.DatetimeIndex):
            try: hist_df.index = pd.to_datetime(hist_df.index)
            except Exception: pass
        cutoff = datetime.now() - timedelta(days=months*30)
        df = hist_df[hist_df.index >= cutoff]
        if df.empty: return None
        series = df[col].dropna(); values = series.tolist(); n = len(values)
        stride = math.ceil(n / max_points) if n > max_points else 1
        sampled = values[::stride]; base = sampled[0]
        if base == 0: base = next((v for v in sampled if v != 0), 1.0)
        norm_seq = [int(round(v / base * 1000)) for v in sampled]
        stats_min, stats_max = min(values), max(values)
        stats_mean = sum(values)/n
        stats_std = (sum((v-stats_mean)**2 for v in values)/(n-1))**0.5 if n>1 else 0.0
        stats_ret = (values[-1]/values[0]-1.0) if values[0]!=0 else 0.0
        annual_factor = 365/(months*30) if months>0 else 1
        stats_vol = stats_std/stats_mean*math.sqrt(annual_factor) if stats_mean!=0 else 0.0
        return {'seq':','.join(map(str,norm_seq)),'base':round(base,4),'len':n,'stride':stride,'points':len(norm_seq),
                'min':round(stats_min,4),'max':round(stats_max,4),'ret':round(stats_ret,4),'std':round(stats_std,4),'vol':round(stats_vol,4)}

    # Toon 压缩提示词 -------------------------------------------------
    def _build_toon_prompt(self, report: Dict[str, Any], hist_info: Optional[Dict[str, Any]] = None) -> str:
        """生成 Toon 紧凑格式提示词
        结构：
            M: 基本信息 (代码/名称)
            P: 价格信息 (日期/开高低收/成交量)
            S: 技术信号 (kdj, macd, rsi => 1/0)
            SUM: 汇总 (信号数/激活列表/压缩建议)
            TS: 历史统计 (len/pts/stride/base/ret/min/max/std/vol)
            SEQ: 压缩历史序列 (整数列表字符串)
        Args:
            report: 结构化报告
            hist_info: 由 _compress_history 返回的历史压缩信息
        Returns:
            str: Toon 格式单行字符串
        """
        meta = report.get('meta', {}); price = report.get('price', {}); signals = report.get('signals', {}); summary = report.get('summary', {})
        kdj = 1 if signals.get('kdj_golden_cross') else 0
        macd = 1 if signals.get('macd_golden_cross') else 0
        rsi = 1 if signals.get('rsi_oversold') else 0
        acts = summary.get('active_signals', []); act_str = '|'.join(acts) if acts else ''
        suggestion = summary.get('suggestion', '')
        for k,v in {'双金叉':'DXC','突破':'TP','少量试探':'SLST','继续观察':'GJGC','共振':'GZ'}.items(): suggestion = suggestion.replace(k,v)
        suggestion = suggestion.strip()
        toon = (f"M:c={meta.get('stock_code','')},n={meta.get('stock_name','')}"
                f";P:d={price.get('date','')},o={price.get('open',0):.2f},h={price.get('high',0):.2f},l={price.get('low',0):.2f},c={price.get('close',0):.2f},v={int(price.get('volume',0))}"
                f";S:kdj={kdj},macd={macd},rsi={rsi}" 
                f";SUM:cnt={summary.get('signal_count',0)},act={act_str},sug={suggestion}")
        if hist_info:
            toon += (f";TS:len={hist_info['len']},pts={hist_info['points']},stride={hist_info['stride']},base={hist_info['base']},ret={hist_info['ret']},min={hist_info['min']},max={hist_info['max']},std={hist_info['std']},vol={hist_info['vol']}" 
                     f";SEQ:{hist_info['seq']}")
        return toon

    def _build_system_prompt(self):
        """生成系统提示词"""
        system_prompt = "你是一个专业的股票分析助手，擅长根据技术指标和历史数据提供简洁有力的交易建议。"
        return system_prompt

__all__ = ['AIClient']
