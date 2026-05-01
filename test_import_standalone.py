#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试导入 init_db_standalone 时的行为"""

import sys
import os

print("Before importing init_db_standalone...")
db_path = 'oa.db'
print(f"DB exists: {os.path.exists(db_path)}")

# 测试导入 init_db_standalone
print("\nNow importing init_db_standalone...")
from init_db_standalone import app

print(f"\nAfter import, DB exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    print(f"DB was created during import!")
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f'Tables: {[t[0] for t in tables]}')
    conn.close()
else:
    print(f"DB not created during import - good!")
