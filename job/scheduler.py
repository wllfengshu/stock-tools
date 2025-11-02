#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
scheduler.py
简单调度：按照 config 中 schedule_times 执行全流程（示例）
"""
import os, sys, time
from datetime import datetime
from typing import List, Optional, Dict, Any

from job.config import GLOBAL_CONFIG
from job.data_fetcher import DataFetcher
from job.indicator_calculator import IndicatorCalculator
from job.report_generator import ReportGenerator
from job.ai_client import AIClient
from job.message_sender import MessageSender

class Scheduler:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.calc = IndicatorCalculator()
        self.reporter = ReportGenerator()
        self.ai = AIClient()
        self.sender = MessageSender()
        print("✅ Scheduler 初始化完成")

    def _should_run_now(self):
        now = datetime.now().strftime('%H:%M')
        return now in GLOBAL_CONFIG.schedule_times

    def run_once_for_stock(self, code: str, name: str) -> Dict[str, Any]:
        print(f"\n=== 调度执行 {code} {name} ===")
        try:
            df = self.fetcher.fetch_stock_hist(code, months=GLOBAL_CONFIG.months)
            indicators = self.calc.calculate_indicators(df)
            report = self.reporter.generate(code, name, df, indicators)
            ai_result = self.ai.call(report, df, use_ai=True) # 开一下ai
            self.sender.send(ai_result, use_push=False)
            return {"code": code, "name": name, "report": report, "ai": ai_result, "success": True}
        except Exception as e:
            print(f"❌ {code} 处理失败: {e}")
            return {"code": code, "name": name, "error": str(e), "success": False}

    def loop(self):
        print("⏳ 调度启动，计划时间:", GLOBAL_CONFIG.schedule_times)
        while True:
            if self._should_run_now():
                for s in GLOBAL_CONFIG.get_stock_list():
                    self.run_once_for_stock(s['code'], s['name'])
                time.sleep(65)  # 防止同一分钟重复执行
            else:
                time.sleep(5)

if __name__ == '__main__':
    print("🚀 启动调度程序...")
    scheduler = Scheduler()
    scheduler.run_once_for_stock("300568", "星源材质")
