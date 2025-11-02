#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
message_sender.py
消息发送：控制台输出 + 聚合云推。

安全：使用环境变量提供聚合云推送配置
  JUHE_PUSH_URL     (默认 https://tui.juhe.cn/api/plus/pushApi)
  JUHE_PUSH_TOKEN   (必需)
  JUHE_SERVICE_ID   (必需)
"""
from typing import Dict, Any, Optional
import os
import json
import requests

class MessageSender:
    def __init__(self, channel: str = 'console'):
        self.channel = channel
        self.push_url = os.getenv('JUHE_PUSH_URL', 'https://tui.juhe.cn/api/plus/pushApi')
        self.push_token = os.getenv('JUHE_PUSH_TOKEN', "64d8fd0d2c72437449e52192192e47c6")
        self.service_id = os.getenv('JUHE_SERVICE_ID', "izbXRjX")
        print(f"✅ MessageSender 初始化: channel={channel}")

    def send(self, ai_result: Dict[str, Any], title: str = 'AI分析结果', use_push: bool = True) -> bool:
        """发送消息
        Args:
            ai_result: AIClient 返回字典
            title: 推送标题
            use_push: 是否尝试聚合云推送（需配置环境变量）
        Returns:
            bool: 是否成功
        """
        summary = ai_result.get('ai_summary') or ai_result.get('prompt')
        print("\n===== 消息推送 =====")
        print(f"渠道: {self.channel}")
        print(f"标题: {title}")
        print(f"内容:\n{summary}")
        print("===================\n")

        if use_push:
            if not self.push_token or not self.service_id:
                print("⚠️ 缺少推送配置 JUHE_PUSH_TOKEN 或 JUHE_SERVICE_ID，已跳过云推送")
                return True
            if requests is None:
                print("⚠️ requests 未安装，无法执行云推送")
                return True
            payload = {
                'token': self.push_token,
                'serviceId': self.service_id,
                'title': title,
                'content': summary[:2000]  # 避免过长
            }
            try:
                resp = requests.post(self.push_url, json=payload, timeout=15)
                if resp.status_code >= 400:
                    print(f"❌ 云推送失败 HTTP {resp.status_code}: {resp.text[:300]}")
                else:
                    data = resp.json()
                    print(f"✅ 云推送响应: {json.dumps(data, ensure_ascii=False)[:300]}")
            except Exception as e:
                print(f"❌ 云推送异常: {e}")
        return True

__all__ = ['MessageSender']
