#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试知识库搜索显示问题
"""

import os
import sys
import sqlite3
from pathlib import Path

# 添加到Python路径
base_dir = Path(__file__).parent.parent.absolute()
db_path = base_dir / "instance" / "oa.db"

print("=" * 60)
print("调试知识库搜索显示问题")
print("=" * 60)

if not db_path.exists():
    print(f"数据库文件不存在: {db_path}")
    sys.exit(1)

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("1. 检查knowledge_files表结构:")
    cursor.execute("PRAGMA table_info(knowledge_files)")
    columns = cursor.fetchall()
    print(f"   列数: {len(columns)}")
    
    # 检查关键列
    col_names = [col[1] for col in columns]
    print(f"   关键列检查:")
    print(f"     id: {'存在' if 'id' in col_names else '缺失'}")
    print(f"     filename: {'存在' if 'filename' in col_names else '缺失'}")
    print(f"     content_text: {'存在' if 'content_text' in col_names else '缺失'}")
    print(f"     keywords: {'存在' if 'keywords' in col_names else '缺失'}")
    print(f"     file_type: {'存在' if 'file_type' in col_names else '缺失'}")
    
    print("\n2. 检查FTS表结构和内容:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%knowledge_files_fts%'")
    fts_tables = cursor.fetchall()
    
    for table in fts_tables:
        table_name = table[0]
        print(f"\n   表: {table_name}")
        
        if table_name == 'knowledge_files_fts':
            # 检查结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            fts_columns = cursor.fetchall()
            print(f"     列: {len(fts_columns)}")
            for col in fts_columns:
                print(f"       {col[1]}: {col[2]}")
            
            # 检查内容
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"     记录数: {count}")
            
            # 查看一些示例数据
            if count > 0:
                cursor.execute(f"SELECT file_id, title, substr(content, 1, 50) FROM {table_name} LIMIT 3")
                samples = cursor.fetchall()
                print(f"     示例记录:")
                for file_id, title, content_preview in samples:
                    print(f"       ID:{file_id}, 标题:'{title}', 内容:'{content_preview}...'")
            
            # 测试搜索
            print(f"\n     FTS搜索测试:")
            test_keywords = ['测试', '文档', '文件', '工作']
            for keyword in test_keywords:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {table_name} MATCH ?", (keyword,))
                    match_count = cursor.fetchone()[0]
                    print(f"       关键词'{keyword}': {match_count} 条匹配")
                    
                    if match_count > 0:
                        cursor.execute(f"""
                        SELECT file_id, title, substr(content, 1, 50), bm25({table_name}) as rank 
                        FROM {table_name} 
                        WHERE {table_name} MATCH ? 
                        ORDER BY rank 
                        LIMIT 1
                        """, (keyword,))
                        best_match = cursor.fetchone()
                        if best_match:
                            print(f"         最佳匹配: ID:{best_match[0]}, 标题:'{best_match[1]}', 得分:{best_match[3]:.2f}")
                except Exception as e:
                    print(f"       搜索'{keyword}'失败: {str(e)[:50]}")
    
    print("\n3. 检查知识库关联:")
    
    # 检查knowledge_files和knowledge_bases表的关联
    cursor.execute("""
    SELECT kf.id, kf.filename, kb.name as kb_name, kb.type as kb_type
    FROM knowledge_files kf
    LEFT JOIN knowledge_bases kb ON kf.knowledge_base_id = kb.id
    WHERE kf.status = 'approved'
    LIMIT 5
    """)
    
    file_records = cursor.fetchall()
    print(f"   已审核文件示例 ({len(file_records)} 条):")
    for id_num, filename, kb_name, kb_type in file_records:
        print(f"     ID:{id_num}, 文件名:'{filename}', 知识库:'{kb_name}', 类型:{kb_type}")
    
    print("\n4. 模拟搜索结果页面数据流:")
    
    # 模拟真实的搜索查询
    search_keyword = "测试"
    print(f"   搜索关键词: '{search_keyword}'")
    
    # 直接使用SQL进行FTS搜索
    try:
        cursor.execute("""
        SELECT 
            kf.id as file_id,
            kff.title,
            substr(kff.content, 1, 300) as snippet,
            kb.name as kb_name,
            kb.type as kb_type,
            kf.file_type,
            kf.tags,
            bm25(kff) as rank
        FROM knowledge_files_fts kff
        JOIN knowledge_files kf ON kf.id = kff.file_id
        JOIN knowledge_bases kb ON kb.id = kf.knowledge_base_id
        WHERE kff MATCH ? AND kf.status = 'approved'
        ORDER BY rank
        LIMIT 5
        """, (search_keyword,))
        
        search_results = cursor.fetchall()
        print(f"   SQL直接搜索结果: {len(search_results)} 条")
        
        if search_results:
            for i, (file_id, title, snippet, kb_name, kb_type, file_type, tags, rank) in enumerate(search_results, 1):
                print(f"     [{i}] 文件ID:{file_id}")
                print(f"         标题: '{title}'")
                print(f"         知识库: '{kb_name}' ({kb_type})")
                print(f"         文件类型: {file_type}")
                print(f"         标签: {tags}")
                print(f"         得分: {rank:.2f}")
                print(f"         摘要: '{snippet[:50] if snippet else '无'}...'")
        else:
            print(f"   无搜索结果")
            
            # 检查LIKE搜索作为后备
            cursor.execute("""
            SELECT COUNT(*) 
            FROM knowledge_files kf
            JOIN knowledge_bases kb ON kb.id = kf.knowledge_base_id
            WHERE kf.status = 'approved' 
            AND (kf.filename LIKE ? OR kf.content_text LIKE ? OR kf.keywords LIKE ?)
            """, (f'%{search_keyword}%', f'%{search_keyword}%', f'%{search_keyword}%'))
            
            like_count = cursor.fetchone()[0]
            print(f"   LIKE后备搜索: {like_count} 条匹配")
    
    except Exception as e:
        print(f"   SQL搜索失败: {e}")
    
    print("\n5. 检查模板所需字段:")
    
    # 从搜索结果模板中需要的字段
    template_fields = ['file_id', 'title', 'snippet', 'kb_name', 'kb_type', 'file_type', 'tags', 'rank']
    print(f"   模板需要字段: {template_fields}")
    
    # 检查实际查出的数据
    if 'search_results' in locals() and search_results:
        sample_result = search_results[0] if search_results else None
        if sample_result:
            print(f"   实际字段匹配检查:")
            for i, field in enumerate(template_fields):
                if i < len(sample_result):
                    value = sample_result[i]
                    value_str = str(value)[:50] if value else 'None'
                    print(f"     {field}: {value_str}")
                else:
                    print(f"     {field}: 字段不存在")
    
    conn.close()
    
except Exception as e:
    print(f"调试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("调试完成")
print("=" * 60)