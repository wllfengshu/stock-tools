#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
启动脚本
"""

from web_server import app

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)
