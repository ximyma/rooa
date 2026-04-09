#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查数据库状态
"""

import os
import sys
import sqlite3
from pathlib import Path

base_dir = Path(__file__).parent.parent.absolute()

print("=" * 60)
print("检查数据库状态")
print("=" * 60)

db_files = []
for db_name in ['oa.db', 'ooa.db', 'instance/knowledge_base.db']:
    db_path = base_dir / db_name
    if db_path.exists():
        db_files.append((db_name, db_path))

if not db_files:
    print("未找到数据库文件")
    sys.exit(1)

for db_name, db_path in db_files:
    print(f"\n检查数据库: {db_name}")
    print(f"文件路径: {db_path}")
    print(f"文件大小: {db_path.stat().st_size:,} 字节")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"表数量: {len(tables)}")
        
        if tables:
            print("表列表:")
            for i, table in enumerate(tables, 1):
                # 检查记录数
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"  {i:3d}. {table:30s} - {count:5d} 条记录")
                    
                    # 如果是knowledge_files，检查详细情况
                    if table == 'knowledge_files':
                        cursor.execute("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(CASE WHEN extracted_text IS NOT NULL AND LENGTH(extracted_text) > 0 THEN 1 END) as has_text,
                            COUNT(CASE WHEN keywords IS NOT NULL AND LENGTH(keywords) > 0 THEN 1 END) as has_keywords
                        FROM knowledge_files
                        """)
                        total, has_text, has_keywords = cursor.fetchone()
                        print(f"    文本提取: {has_text}/{total} ({has_text/max(total,1)*100:.1f}%)")
                        print(f"    关键词生成: {has_keywords}/{total} ({has_keywords/max(total,1)*100:.1f}%)")
                        
                except Exception as e:
                    print(f"  {i:3d}. {table:30s} - 检查失败: {str(e)[:50]}")
        
        # 检查FTS表
        fts_tables = [t for t in tables if 'fts' in t.lower()]
        if fts_tables:
            print("\nFTS全文索引表:")
            for fts_table in fts_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {fts_table}")
                    count = cursor.fetchone()[0]
                    print(f"  {fts_table}: {count} 条索引记录")
                    
                    # 测试FTS查询
                    cursor.execute(f"SELECT COUNT(*) FROM {fts_table} WHERE {fts_table} MATCH '测试'")
                    test_count = cursor.fetchone()[0]
                    print(f"    包含'测试'的记录: {test_count}")
                except Exception as e:
                    print(f"  {fts_table}: 检查失败 - {str(e)[:50]}")
        
        # 检查档案表
        archive_tables = [t for t in tables if 'archive' in t.lower()]
        if archive_tables:
            print(f"\n档案相关表 ({len(archive_tables)} 个):")
            for table in archive_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} 条记录")
        
        conn.close()
        
    except Exception as e:
        print(f"数据库连接失败: {e}")

print("\n" + "=" * 60)
print("数据库检查完成")
print("=" * 60)