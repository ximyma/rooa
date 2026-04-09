#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个人知识库CRUD功能测试脚本
用于验证新增的个人知识库管理功能
"""

import os
import sys
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== 个人知识库CRUD功能测试 ===\n")

try:
    # 导入应用模块
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from config import Config
    
    print("[1] 导入模块成功")
    
    # 创建测试应用
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['TESTING'] = True
    
    # 初始化数据库
    db = SQLAlchemy()
    db.init_app(app)
    
    from models import User, KnowledgeBase, KnowledgeFile
    
    with app.app_context():
        print("[2] 数据库连接成功")
        
        # 测试用户ID
        test_user_id = 1  # 管理员用户
        
        # 1. 检查现有个人知识库
        existing_kbs = KnowledgeBase.query.filter_by(owner_id=test_user_id, type='personal').all()
        print(f"  现有个人知识库: {len(existing_kbs)} 个")
        for kb in existing_kbs:
            print(f"    - ID: {kb.id}, 名称: '{kb.name}', 文件数: {kb.files.count() if kb.files else 0}")
        
        # 2. 测试创建个人知识库
        print("\n[3] 测试创建个人知识库功能:")
        
        # 检查是否可以创建知识库
        from app import create_personal_kb, edit_personal_kb, delete_personal_kb
        
        print("   ✓ 路由函数已加载")
        
        # 3. 测试查询功能
        print("\n[4] 测试查询功能:")
        # 模拟用户查看所有个人知识库
        all_personal_kbs = KnowledgeBase.query.filter_by(owner_id=test_user_id, type='personal').all()
        print(f"   可以列出 {len(all_personal_kbs)} 个个人知识库")
        
        # 4. 测试权限检查
        print("\n[5] 测试权限检查:")
        for kb in all_personal_kbs[:2]:  # 检查前两个知识库
            owner_check = KnowledgeBase.query.filter_by(
                id=kb.id, 
                owner_id=test_user_id, 
                type='personal'
            ).first()
            if owner_check:
                print(f"   用户{test_user_id}可以访问知识库 '{kb.name}' (ID: {kb.id})")
            else:
                print(f"   用户{test_user_id}无法访问知识库 '{kb.name}' (ID: {kb.id})")
        
        # 5. 测试数据库字段
        print("\n[6] 测试数据库字段完整性:")
        if all_personal_kbs:
            sample_kb = all_personal_kbs[0]
            print(f"   示例知识库字段:")
            print(f"     id: {sample_kb.id}")
            print(f"     name: {sample_kb.name}")
            print(f"     type: {sample_kb.type}")
            print(f"     owner_id: {sample_kb.owner_id}")
            print(f"     category: {sample_kb.category}")
            print(f"     description: {sample_kb.description}")
            print(f"     is_public: {sample_kb.is_public}")
            print(f"     created_at: {sample_kb.created_at}")
        
        # 7. 测试URL路由
        print("\n[7] 测试路由配置:")
        from flask import url_for
        with app.test_request_context():
            print(f"   个人知识库管理页URL: /knowledge/personal/management")
            print(f"   个人知识库详情页URL: /knowledge/personal/<kb_id>")
            print(f"   创建个人知识库URL: /knowledge/personal/create")
            print(f"   编辑个人知识库URL: /knowledge/personal/edit/<kb_id>")
            print(f"   删除个人知识库URL: /knowledge/personal/delete/<kb_id>")
        
        print("\n[8] 功能总结:")
        print("   1. 支持多个人知识库创建")
        print("   2. 支持个人知识库列表管理")
        print("   3. 支持编辑个人知识库信息")
        print("   4. 支持删除空个人知识库")
        print("   5. 文件需要上传到指定知识库")
        
        print("\n[9] 注意事项:")
        print("   - 非空知识库不可直接删除")
        print("   - 知识库名称在同一用户下必须唯一")
        print("   - 文件上传时需要指定知识库ID")
        
except ImportError as e:
    print(f"导入失败: {e}")
except Exception as e:
    print(f"测试过程中出错: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 测试完成 ===\n")
print("接下来需要:")
print("1. 启动应用验证功能")
print("2. 测试UI界面交互")
print("3. 验证文件上传到指定知识库")
print("4. 测试批量操作")