#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试知识库搜索功能
"""

import os
import sys
from pathlib import Path

# 添加到Python路径
base_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(base_dir))

print("=" * 60)
print("测试知识库搜索功能")
print("=" * 60)

try:
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from config import Config
    
    # 创建应用
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 初始化数据库
    db = SQLAlchemy()
    db.init_app(app)
    
    with app.app_context():
        # 导入搜索函数
        from app import search_knowledge_fts, _search_knowledge_like
        
        print("1. 测试搜索关键词: '测试'")
        
        # 测试FTS搜索
        results = search_knowledge_fts(keyword='测试', page=1, page_size=10)
        print(f"   FTS搜索结果: {results.get('total', 0)} 条")
        print(f"   搜索模式: {results.get('mode', 'unknown')}")
        
        if results.get('results'):
            print(f"   前3条结果:")
            for i, r in enumerate(results['results'][:3], 1):
                print(f"     [{i}] 文件ID: {r.get('file_id')}")
                print(f"         标题: {r.get('title', '无标题')}")
                print(f"         知识库: {r.get('kb_name', '未知')}")
                print(f"         类型: {r.get('kb_type', '未知')}")
                print(f"         文件类型: {r.get('file_type', '未知')}")
                print(f"         标签: {r.get('tags', '无')}")
                print(f"         摘要: {r.get('snippet', '无')[:50]}...")
        else:
            print("   无结果")
        
        print("\n2. 检查knowledge_files表中的数据:")
        
        from models import KnowledgeFile
        import random
        
        # 获取一些记录
        kf_records = KnowledgeFile.query.limit(5).all()
        print(f"   数据库中前5条记录:")
        for i, kf in enumerate(kf_records, 1):
            print(f"     [{i}] ID:{kf.id} 文件名:{kf.filename}")
            print(f"         原始名:{kf.original_name}")
            print(f"         文件类型:{kf.file_type}")
            print(f"         文件大小:{kf.file_size:,} 字节")
            print(f"         状态:{kf.status}")
            print(f"         上传时间:{kf.upload_time}")
            print(f"         文本长度:{len(kf.content_text) if kf.content_text else 0:,} 字符")
            print(f"         关键词:{kf.keywords[:50] if kf.keywords else '无'}")
        
        print("\n3. 检查FTS表内容:")
        
        import sqlite3
        db_path = base_dir / "instance" / "oa.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT file_id, title, substr(content, 1, 100) as preview FROM knowledge_files_fts LIMIT 5")
        fts_rows = cursor.fetchall()
        
        print(f"   FTS表中前5条记录:")
        for i, (file_id, title, preview) in enumerate(fts_rows, 1):
            print(f"     [{i}] 文件ID:{file_id}")
            print(f"         标题:{title}")
            print(f"         预览:{preview[:80] if preview else '无'}...")
        
        conn.close()
        
        print("\n4. 测试具体问题: 搜索结果显示")
        
        # 模拟搜索请求
        print("   模拟搜索请求流程...")
        
        # 检查FTS索引是否有内容
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM knowledge_files_fts WHERE knowledge_files_fts MATCH '测试'")
        fts_match_count = cursor.fetchone()[0]
        print(f"   FTS中匹配'测试'的记录数: {fts_match_count}")
        
        cursor.execute("""
        SELECT snippet(knowledge_files_fts, 0, '<b>', '</b>', '...', 3) as snippet 
        FROM knowledge_files_fts 
        WHERE knowledge_files_fts MATCH '测试' 
        LIMIT 1
        """)
        
        sample_match = cursor.fetchone()
        if sample_match and sample_match[0]:
            print(f"   FTS匹配示例: {sample_match[0][:100]}")
        else:
            print(f"   FTS无匹配示例")
        
        conn.close()
        
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)