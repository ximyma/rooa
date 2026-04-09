#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查content_text列内容
"""

import os
import sys
import sqlite3
from pathlib import Path

base_dir = Path(__file__).parent.parent.absolute()
db_path = base_dir / "instance" / "oa.db"

print("=" * 60)
print("检查content_text列内容")
print("=" * 60)

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 检查content_text列的内容分布
    print("1. content_text列内容分析:")
    
    cursor.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN content_text IS NULL OR content_text = '' THEN 1 END) as empty,
        COUNT(CASE WHEN content_text LIKE '%解析失败%' THEN 1 END) as parse_failed,
        COUNT(CASE WHEN content_text NOT LIKE '%解析失败%' AND content_text IS NOT NULL AND content_text != '' THEN 1 END) as has_content
    FROM knowledge_files
    """)
    
    total, empty, parse_failed, has_content = cursor.fetchone()
    
    print(f"   总记录数: {total}")
    print(f"   空内容: {empty} ({empty/max(total,1)*100:.1f}%)")
    print(f"   解析失败: {parse_failed} ({parse_failed/max(total,1)*100:.1f}%)")
    print(f"   有内容: {has_content} ({has_content/max(total,1)*100:.1f}%)")
    
    print("\n2. 检查解析失败的示例:")
    cursor.execute("""
    SELECT id, filename, file_type, substr(content_text, 1, 100) as preview
    FROM knowledge_files 
    WHERE content_text LIKE '%解析失败%'
    LIMIT 5
    """)
    
    failed_records = cursor.fetchall()
    for id_num, filename, file_type, preview in failed_records:
        print(f"   ID:{id_num} 文件名:{filename} 类型:{file_type}")
        print(f"   内容预览: {preview}")
    
    print("\n3. 检查有内容的示例:")
    cursor.execute("""
    SELECT id, filename, file_type, substr(content_text, 1, 150) as preview
    FROM knowledge_files 
    WHERE content_text NOT LIKE '%解析失败%' 
    AND content_text IS NOT NULL 
    AND content_text != ''
    ORDER BY LENGTH(content_text) DESC
    LIMIT 5
    """)
    
    valid_records = cursor.fetchall()
    for id_num, filename, file_type, preview in valid_records:
        print(f"   ID:{id_num} 文件名:{filename} 类型:{file_type}")
        if preview:
            print(f"   内容预览: {preview[:100]}...")
        print(f"   长度: {len(preview)} 字符")
    
    print("\n4. 检查关键词列:")
    cursor.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN keywords IS NULL OR keywords = '' THEN 1 END) as empty_keywords,
        COUNT(CASE WHEN keywords LIKE '%测试%' THEN 1 END) as has_test_keyword
    FROM knowledge_files
    """)
    
    total_kw, empty_kw, has_test_kw = cursor.fetchone()
    print(f"   总记录数: {total_kw}")
    print(f"   空关键词: {empty_kw} ({empty_kw/max(total_kw,1)*100:.1f}%)")
    print(f"   包含'测试'关键词: {has_test_kw}")
    
    print("\n5. 检查文件类型分布:")
    cursor.execute("""
    SELECT file_type, COUNT(*) as count
    FROM knowledge_files
    GROUP BY file_type
    ORDER BY count DESC
    """)
    
    type_dist = cursor.fetchall()
    for file_type, count in type_dist:
        print(f"   {file_type or '未知'}: {count} 条")
    
    print("\n6. 搜索问题诊断:")
    
    # 检查哪些文件应该包含"测试"这个词
    print("   查找可能包含'测试'的文件:")
    
    # 从文件名中查找
    cursor.execute("""
    SELECT id, filename
    FROM knowledge_files
    WHERE filename LIKE '%测试%' OR filename LIKE '%test%'
    LIMIT 10
    """)
    
    matching_files = cursor.fetchall()
    print(f"   文件名包含'测试'的文件: {len(matching_files)} 个")
    for id_num, filename in matching_files[:5]:
        print(f"     ID:{id_num} 文件名:{filename}")
    
    # 检查知识库搜索结果的LIKE后备机制
    print(f"\n7. 模拟LIKE搜索结果:")
    
    test_keyword = "测试"
    cursor.execute("""
    SELECT kf.id, kf.filename, kb.name, substr(kf.content_text, 1, 50) as preview
    FROM knowledge_files kf
    JOIN knowledge_bases kb ON kf.knowledge_base_id = kb.id
    WHERE kf.status = 'approved'
    AND (kf.filename LIKE ? OR kf.content_text LIKE ? OR kf.keywords LIKE ?)
    LIMIT 5
    """, (f'%{test_keyword}%', f'%{test_keyword}%', f'%{test_keyword}%'))
    
    like_results = cursor.fetchall()
    print(f"   LIKE搜索'{test_keyword}'结果: {len(like_results)} 条")
    for id_num, filename, kb_name, preview in like_results:
        print(f"     ID:{id_num} 文件名:{filename} 知识库:{kb_name}")
        if preview:
            print(f"     预览: {preview}")
    
    conn.close()
    
except Exception as e:
    print(f"检查失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)