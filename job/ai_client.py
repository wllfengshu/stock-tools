#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
ai_client.py
AI客户端：专注于与AI模型的交互
职责：
  1. 管理API连接配置
  2. 发送请求到AI模型
  3. 处理响应和错误
数据源：仅从ReportGenerator获取准备好的数据
"""
import os
import time
import json
from typing import Dict, Any, Optional
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
        安全说明：真实token不应写入代码，这里默认读取环境变量；若未提供真实token将在调用时给出错误提示。
        """
        # 真实调用所需配置
        self.api_url = api_url or os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.api_token = api_token or os.getenv('SILICONFLOW_API_TOKEN', 'sk-nypfpxrbfrlrtxbzczpkrgexpxjnaitxbubuojjhtcxgedjm')
        self.model = model or os.getenv('SILICONFLOW_MODEL', 'deepseek-ai/DeepSeek-V3')
        self.timeout = timeout
        self.retries = max(0, retries)
        print(f"✅ AIClient 初始化: model={self.model}, retries={self.retries}")

    def call(self, ai_data: Dict[str, Any], use_ai: bool = True,
             temperature: float = 0.7, max_tokens: int = 1024) -> Dict[str, Any]:
        """
        统一调用入口，支持ReportGenerator.prepare_ai_data_from_signal()输出
        ai_data: {'prompt', 'system_prompt', ...}
        """
        prompt = ai_data.get('prompt', '')
        system_prompt = ai_data.get('system_prompt', '')
        result: Dict[str, Any] = {
            'prompt': prompt,
            'model': self.model,
            'system_prompt': system_prompt
        }
        print("="*80)
        print(f"🚀 调用 AI 模型: model={self.model}")
        print(result)
        if not self.api_token:
            result['error'] = '缺少 API Token (SILICONFLOW_API_TOKEN)'
            return result
        payload = self._build_payload(system_prompt, prompt, temperature, max_tokens)
        if use_ai:
            api_response = self._request_api(payload)
            result.update(api_response)
        return result

    def _build_payload(self, system_prompt: str, user_prompt: str,
                      temperature: float, max_tokens: int) -> Dict[str, Any]:
        """构建硅基流动兼容的请求体
        Args:
            system_prompt: 系统级角色提示
            user_prompt: 用户主体内容（Toon或人类可读）
            temperature: 随机性参数
            max_tokens: 最大生成token限制
        Returns:
            dict: 可直接序列化为JSON的请求体。
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
                    return {
                        'error': f'HTTP {resp.status_code}',
                        'details': resp.text[:500],
                        'latency': elapsed
                    }

                data = resp.json()
                text = self._extract_text(data)
                return {
                    'ai_summary': text,
                    'raw_response': data,
                    'latency': elapsed
                }
            except requests.exceptions.Timeout as e:
                last_error = f'Timeout: {e}'
            except requests.exceptions.RequestException as e:
                last_error = f'RequestException: {e}'
            except json.JSONDecodeError as e:
                last_error = f'JSONDecodeError: {e}'

            time.sleep(1.0 * (attempt + 1))

        return {
            'error': 'API调用失败',
            'details': last_error,
            'latency': None
        }

    def _extract_text(self, response: Dict[str, Any]) -> str:
        """从模型返回结构中提取文本
        兼容OpenAI风格：response['choices'][0]['message']['content']
        若结构异常或无内容，则返回部分原始JSON或错误信息。
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


__all__ = ['AIClient']
