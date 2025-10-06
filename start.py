#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
启动脚本 - 智能选择开发或生产环境
"""

from web_server import app

app.run(debug=False, host='0.0.0.0', port=8080)
