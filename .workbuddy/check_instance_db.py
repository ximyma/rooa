#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查instance目录下的oa.db数据库
"""

import os
import sys
import sqlite3
from pathlib import Path

# 添加到Python路径
base_dir = Path(__file__).parent.parent.absolute()
instance_dir = base_dir / "instance"

print("=" * 60)
print("检查instance目录数据库")
print("=" * 60)

db_files = []
for db_name in ['oa.db', 'ooa.db']:
    db_path = instance_dir / db_name
    if db_path.exists():
        db_files.append((db_name, db_path))

if not db_files:
    print("instance目录下未找到数据库文件")
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
        
        # 检查knowledge_files表
        if 'knowledge_files' in tables:
            print("\n[1] 检查knowledge_files表:")
            cursor.execute("SELECT COUNT(*) FROM knowledge_files")
            count = cursor.fetchone()[0]
            print(f"    记录数: {count}")
            
            if count > 0:
                # 检查文本提取情况
                cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN extracted_text IS NOT NULL AND LENGTH(extracted_text) > 0 THEN 1 END) as has_text,
                    COUNT(CASE WHEN keywords IS NOT NULL AND LENGTH(keywords) > 0 THEN 1 END) as has_keywords
                FROM knowledge_files
                """)
                total, has_text, has_keywords = cursor.fetchone()
                print(f"    有提取文本的记录: {has_text}/{total} ({has_text/max(total,1)*100:.1f}%)")
                print(f"    有关键词的记录: {has_keywords}/{total} ({has_keywords/max(total,1)*100:.1f}%)")
                
                # 查看最新记录
                cursor.execute("""
                SELECT id, file_name, file_type, file_size, 
                       LENGTH(extracted_text) as text_len, keywords,
                       upload_time
                FROM knowledge_files 
                ORDER BY upload_time DESC 
                LIMIT 5
                """)
                
                rows = cursor.fetchall()
                print(f"\n    最近5条记录:")
                for i, (id_num, name, ftype, size, text_len, keywords, upload_time) in enumerate(rows, 1):
                    print(f"    [{i}] ID:{id_num} {name} ({ftype}, {size:,} 字节)")
                    print(f"        文本长度: {text_len:,} 字符")
                    print(f"        关键词: {keywords[:50] if keywords else '无'}")
                    print(f"        上传时间: {upload_time}")
        else:
            print("\n[1] knowledge_files表: 不存在")
        
        # 检查FTS表
        fts_tables = [t for t in tables if 'fts' in t.lower()]
        if fts_tables:
            print(f"\n[2] 检查FTS全文索引表:")
            for fts_table in fts_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {fts_table}")
                count = cursor.fetchone()[0]
                print(f"    {fts_table}: {count} 条索引记录")
                
                # 测试FTS查询
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {fts_table} WHERE {fts_table} MATCH '测试'")
                    test_count = cursor.fetchone()[0]
                    print(f"        包含'测试'的记录: {test_count}")
                    
                    # 更多测试查询
                    cursor.execute(f"""
                    SELECT snippet({fts_table}, 0, '[', ']', '...', 5) as snippet, rank 
                    FROM {fts_table} 
                    WHERE {fts_table} MATCH '测试 OR 文档' 
                    LIMIT 3
                    """)
                    results = cursor.fetchall()
                    if results:
                        print(f"        FTS查询示例结果:")
                        for snippet, rank in results:
                            print(f"          摘要: {snippet[:80]}..., 得分: {rank:.2f}")
                except Exception as e:
                    print(f"        FTS查询测试失败: {e}")
        else:
            print(f"\n[2] FTS全文索引表: 不存在")
        
        # 检查知识库搜索相关表
        knowledge_related = [t for t in tables if 'knowledge' in t.lower()]
        if knowledge_related:
            print(f"\n[3] 知识库相关表 ({len(knowledge_related)} 个):")
            for table in knowledge_related:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"    {table}: {count} 条记录")
        
        # 检查数据库连接配置
        print(f"\n[4] 检查数据库配置:")
        # 读取config.py中的数据库配置
        config_path = base_dir / "config.py"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'SQLALCHEMY_DATABASE_URI' in content:
                    for line in content.split('\n'):
                        if 'SQLALCHEMY_DATABASE_URI' in line:
                            print(f"    数据库URI配置: {line.strip()}")
        
        conn.close()
        
    except Exception as e:
        print(f"数据库连接失败: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("数据库检查完成")
print("=" * 60)