#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""智能服务办公平台 - 启动器"""

import sys
import os
from pathlib import Path

# 添加正确的路径
if getattr(sys, 'frozen', False):
    # 打包后的运行环境
    APP_PATH = Path(sys.executable).parent
else:
    # 开发环境
    APP_PATH = Path(__file__).parent

sys.path.insert(0, str(APP_PATH))

print("="*64)
print("  智能服务办公平台")
print("="*64)
print()
print("正在检查数据库状态...")

# 导入应用
os.chdir(str(APP_PATH))
from app import app, initialize_db
import webbrowser

# 检查数据库是否存在
db_path = APP_PATH / "oa.db"
if not db_path.exists():
    print("数据库不存在，正在初始化...")
    initialize_db()
else:
    print("数据库已存在，跳过初始化")

print()
print("正在启动服务...")
print("服务地址: http://127.0.0.1:5000")
print("按 CTRL+C 可停止服务")
print()

try:
    # 启动后自动打开浏览器
    webbrowser.open("http://127.0.0.1:5000")
except:
    pass

# 启动Flask应用
try:
    from waitress import serve
    print("使用 Waitress WSGI 服务器启动...")
    serve(app, host="127.0.0.1", port=5000)
except ImportError:
    print("使用 Flask 开发服务器启动...")
    app.run(host="127.0.0.1", port=5000, debug=False)
