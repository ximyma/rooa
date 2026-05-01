#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试初始化之前数据库的状态"""

import os
db_path = 'oa.db'
if os.path.exists(db_path):
    print(f'DB file exists at: {os.path.abspath(db_path)}')
    print(f'Size: {os.path.getsize(db_path)} bytes')
    
    # 尝试用 SQLite 打开看看
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f'Tables in DB: {[t[0] for t in tables]}')
    conn.close()
else:
    print(f'DB file does NOT exist at: {os.path.abspath(db_path)}')
    print('Database is clean!')
