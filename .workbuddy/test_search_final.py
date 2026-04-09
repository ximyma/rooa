#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终测试知识库搜索功能
"""

import os
import sys
from pathlib import Path

base_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(base_dir))

print("=" * 60)
print("最终测试知识库搜索功能")
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
        print("1. 应用已初始化")
        
        # 导入搜索函数
        from app import search_knowledge_fts, _search_knowledge_like
        
        print("\n2. 测试搜索功能:")
        test_keywords = ["工作", "文档", "管理", "测试"]
        
        for keyword in test_keywords:
            print(f"\n   搜索关键词: '{keyword}'")
            
            try:
                # 使用FTS搜索
                result = search_knowledge_fts(keyword=keyword, page=1, page_size=5)
                total = result.get('total', 0)
                mode = result.get('mode', 'unknown')
                
                print(f"     结果数: {total} (搜索模式: {mode})")
                
                if total > 0:
                    results = result.get('results', [])
                    print(f"     前{len(results)}条结果:")
                    
                    for i, r in enumerate(results, 1):
                        file_id = r.get('file_id', 'N/A')
                        title = r.get('title', '无标题')
                        kb_name = r.get('kb_name', '未知')
                        file_type = r.get('file_type', '未知')
                        
                        print(f"       [{i}] 文件ID: {file_id}")
                        print(f"            标题: {title[:40] if title else '无标题'}")
                        print(f"            知识库: {kb_name}")
                        print(f"            文件类型: {file_type}")
                        
                        # 检查是否有snippet
                        snippet = r.get('snippet', '')
                        if snippet:
                            # 清理HTML标签
                            clean_snippet = snippet.replace('<mark>', '').replace('</mark>', '')
                            print(f"            摘要: {clean_snippet[:50]}...")
                        
                        # 检查是否包含搜索关键词
                        title_lower = title.lower() if title else ''
                        snippet_lower = snippet.lower() if snippet else ''
                        if keyword.lower() in title_lower or keyword.lower() in snippet_lower:
                            print(f"            (包含关键词)")
                else:
                    print(f"     无搜索结果")
                    
                    # 测试LIKE后备
                    like_result = _search_knowledge_like(keyword=keyword, page=1, page_size=3)
                    like_total = like_result.get('total', 0)
                    print(f"     LIKE后备搜索结果: {like_total} 条")
                    
            except Exception as e:
                print(f"     搜索失败: {str(e)[:100]}")
        
        print("\n3. 分析搜索结果显示问题:")
        
        # 检查模板需要的字段
        print("   模板需要以下字段:")
        required_fields = ['file_id', 'title', 'snippet', 'kb_name', 'kb_type', 'file_type', 'tags']
        for field in required_fields:
            print(f"     - {field}")
        
        # 检查一个具体搜索结果
        print("\n   检查一个具体搜索结果:")
        
        sample_result = search_knowledge_fts(keyword="工作", page=1, page_size=1)
        if sample_result.get('results'):
            first_result = sample_result['results'][0]
            print(f"    第一个结果字段检查:")
            
            missing_fields = []
            for field in required_fields:
                if field in first_result:
                    value = first_result[field]
                    if value:
                        preview = str(value)[:30]
                        print(f"      {field}: {preview}...")
                    else:
                        print(f"      {field}: (空值)")
                else:
                    print(f"      {field}: (缺失)")
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"\n    ⚠️ 警告: 缺失字段: {missing_fields}")
                print(f"     这可能导致模板无法正确显示结果")
            else:
                print(f"\n    ✅ 所有必需字段都存在")
        
        print("\n4. 检查FTS索引内容:")
        
        import sqlite3
        db_path = base_dir / "instance" / "oa.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查FTS表内容
        cursor.execute("SELECT COUNT(*) FROM knowledge_files_fts WHERE content LIKE '%工作%'")
        work_count = cursor.fetchone()[0]
        print(f"   FTS中包含'工作'的记录数: {work_count}")
        
        # 查看匹配示例
        if work_count > 0:
            cursor.execute("""
            SELECT file_id, title, substr(content, 1, 50) as snippet
            FROM knowledge_files_fts
            WHERE content LIKE '%工作%'
            LIMIT 1
            """)
            
            example = cursor.fetchone()
            if example:
                file_id, title, snippet = example
                print(f"   示例匹配:")
                print(f"     文件ID: {file_id}")
                print(f"     标题: {title}")
                print(f"     内容片段: {snippet}")
        
        conn.close()
        
        print("\n5. 结论和建议:")
        print("   - 如果搜索结果有数据但页面不显示，可能是模板渲染问题")
        print("   - 检查 templates/knowledge/search_results.html 模板")
        print("   - 确保搜索结果数据传递正确")
        print("   - 检查是否有JavaScript错误影响显示")
        
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)