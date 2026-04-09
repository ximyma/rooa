#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查knowledge_files表结构
"""

import os
import sys
import sqlite3
from pathlib import Path

# 添加到Python路径
base_dir = Path(__file__).parent.parent.absolute()
db_path = base_dir / "instance" / "oa.db"

print("=" * 60)
print("检查knowledge_files表结构")
print("=" * 60)

if not db_path.exists():
    print(f"数据库文件不存在: {db_path}")
    sys.exit(1)

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 检查knowledge_files表结构
    cursor.execute("PRAGMA table_info(knowledge_files)")
    columns = cursor.fetchall()
    
    print(f"knowledge_files表结构 ({len(columns)} 列):")
    print("序号 | 列名 | 类型 | 非空 | 默认值 | 主键")
    print("-" * 80)
    for col in columns:
        cid, name, ctype, notnull, dflt_value, pk = col
        default_str = str(dflt_value) if dflt_value is not None else "NULL"
        print(f"{cid:3d} | {name:20s} | {ctype:15s} | {notnull} | {default_str[:20]:20s} | {pk}")
    
    # 检查是否有extracted_text和keywords列
    has_extracted_text = any(col[1] == 'extracted_text' for col in columns)
    has_keywords = any(col[1] == 'keywords' for col in columns)
    
    print(f"\n关键列检查:")
    print(f"  extracted_text列: {'存在' if has_extracted_text else '缺失'}")
    print(f"  keywords列: {'存在' if has_keywords else '缺失'}")
    
    # 检查FTS表
    print(f"\n检查FTS相关表:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'")
    fts_tables = cursor.fetchall()
    
    if fts_tables:
        print(f"找到 {len(fts_tables)} 个FTS表:")
        for table in fts_tables:
            table_name = table[0]
            print(f"\n  {table_name}:")
            
            # 检查表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            fts_columns = cursor.fetchall()
            for col in fts_columns:
                cid, name, ctype, notnull, dflt_value, pk = col
                print(f"    {name:20s} | {ctype}")
            
            # 检查内容
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"    记录数: {count}")
    else:
        print("未找到FTS表")
    
    # 检查搜索路由和模板问题
    print(f"\n检查知识库搜索相关问题:")
    
    # 获取几条记录查看实际内容
    cursor.execute("""
    SELECT id, file_name, file_type, file_size, upload_time 
    FROM knowledge_files 
    ORDER BY upload_time DESC 
    LIMIT 5
    """)
    
    sample_records = cursor.fetchall()
    print(f"示例记录 (最近5条):")
    for id_num, name, ftype, size, upload_time in sample_records:
        print(f"  ID:{id_num} 文件名:{name} 类型:{ftype} 大小:{size:,} 时间:{upload_time}")
    
    conn.close()
    
except Exception as e:
    print(f"检查失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("表结构检查完成")
print("=" * 60)