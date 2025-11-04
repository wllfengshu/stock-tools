#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
启动脚本 - 启动Web服务器和定时任务调度器
"""
import threading
import time
from web_server import app
from job.scheduler import Scheduler

def run_scheduler():
    """后台运行定时任务调度器"""
    print("🚀 启动定时任务调度器...")
    scheduler = Scheduler()
    try:
        scheduler.loop()
    except Exception as e:
        print(f"❌ 定时任务调度器异常: {e}")

if __name__ == '__main__':
    # 启动定时任务调度器线程（后台运行）
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("✅ 定时任务调度器已在后台启动")

    # 延迟1秒确保调度器启动完成
    time.sleep(1)

    # 启动Web服务器（主线程）
    print("🌐 启动Web服务器 http://0.0.0.0:3010")
    app.run(debug=False, host='0.0.0.0', port=3010)
