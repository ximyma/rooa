#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试初始化过程，查看表创建后立即有什么数据"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# 设置 Flask 应用
from flask import Flask
from werkzeug.security import generate_password_hash
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///debug_test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'debug-test-key-not-for-production'

# 导入 db
from models import db
db.init_app(app)

print("=== Step 1: Creating tables ===")
with app.app_context():
    db.create_all()
    print("Tables created!")
    
    # 检查各表的数据
    print("\n=== Checking tables ===")
    
    from models import User, Role, Organization, Department, Position
    print(f"Users count: {User.query.count()}")
    print(f"Roles count: {Role.query.count()}")
    print(f"Organizations count: {Organization.query.count()}")
    print(f"Departments count: {Department.query.count()}")
    print(f"Positions count: {Position.query.count()}")

print("\n=== Debug done! ===")

import os
os.remove('debug_test.db')
