# -*- coding:utf-8 -*-
"""
scheduler.py
简单调度：按照 config 中 schedule_times 执行全流程（示例）
"""
import os
import sys
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
            # 1. 获取历史数据
            df = self.fetcher.fetch_stock_hist(code, months=GLOBAL_CONFIG.months)

            # 2. 计算技术指标并生成SignalEntity（新方法：信号自动适配）
            signal_entity = self.calc.calculate_signals(code, name, df, history=df)

            # 3. 准备AI所需数据（由ReportGenerator从SignalEntity直接生成，信号无感扩展）
            ai_data = self.reporter.prepare_ai_data(signal_entity, months=GLOBAL_CONFIG.months)

            # 4. 调用AI（AIClient只负责与AI交互）
            ai_result = self.ai.call(ai_data, use_ai=False)

            # 5. 发送消息
            self.sender.send(ai_result, use_push=False)

            return {"code": code, "name": name, "signal_entity": signal_entity, "ai": ai_result, "success": True}
        except Exception as e:
            print(f"❌ {code} 处理失败: {e}")
            return {"code": code, "name": name, "error": str(e), "success": False}

    def loop(self):
        print("⏰ 调度启动，计划时间:", GLOBAL_CONFIG.schedule_times)
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
    # scheduler.run_once_for_stock("601899", "紫金矿业")
    scheduler.run_once_for_stock("300859", "西域旅游")

