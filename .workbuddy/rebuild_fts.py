#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重建FTS索引
"""

import os
import sys
import sqlite3
from pathlib import Path

base_dir = Path(__file__).parent.parent.absolute()
db_path = base_dir / "instance" / "oa.db"

print("=" * 60)
print("重建FTS索引")
print("=" * 60)

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("1. 检查当前状态...")
    
    # 获取当前FTS记录数
    cursor.execute("SELECT COUNT(*) FROM knowledge_files_fts")
    before_count = cursor.fetchone()[0]
    print(f"   当前FTS记录数: {before_count}")
    
    # 获取应索引的文件数
    cursor.execute("SELECT COUNT(*) FROM knowledge_files WHERE status = 'approved'")
    approved_count = cursor.fetchone()[0]
    print(f"   应索引的文件数: {approved_count}")
    
    print("\n2. 重新构建FTS索引...")
    
    # 删除所有现有FTS记录
    cursor.execute("DELETE FROM knowledge_files_fts")
    print(f"   已删除现有FTS记录")
    
    # 重新插入所有已审核文件
    insert_sql = """
    INSERT INTO knowledge_files_fts(file_id, title, content, kb_name, kb_type, file_type, tags)
    SELECT 
        kf.id,
        kf.filename as title,
        COALESCE(kf.content_text, '') as content,
        COALESCE(kb.name, '') as kb_name,
        COALESCE(kb.type, '') as kb_type,
        COALESCE(kf.file_type, '') as file_type,
        COALESCE(kf.tags, '') as tags
    FROM knowledge_files kf
    LEFT JOIN knowledge_bases kb ON kf.knowledge_base_id = kb.id
    WHERE kf.status = 'approved'
    """
    
    cursor.execute(insert_sql)
    affected_rows = cursor.rowcount
    print(f"   重新索引完成，处理了 {affected_rows} 条记录")
    
    print("\n3. 验证重建结果...")
    
    # 检查重建后的记录数
    cursor.execute("SELECT COUNT(*) FROM knowledge_files_fts")
    after_count = cursor.fetchone()[0]
    print(f"   重建后FTS记录数: {after_count}")
    
    if after_count == approved_count:
        print("   ✅ FTS索引重建成功")
    else:
        print(f"   ⚠️ 警告: 记录数不匹配 (期望: {approved_count}, 实际: {after_count})")
    
    print("\n4. 测试搜索功能...")
    test_keywords = ['测试', '工作', '文档', '管理', '文件']
    
    for keyword in test_keywords:
        try:
            cursor.execute("SELECT COUNT(*) FROM knowledge_files_fts WHERE knowledge_files_fts MATCH ?", (keyword,))
            count = cursor.fetchone()[0]
            print(f"   搜索'{keyword}': {count} 条匹配")
            
            if count > 0:
                cursor.execute("""
                SELECT file_id, title, kb_name, file_type, substr(content, 1, 50) as snippet
                FROM knowledge_files_fts
                WHERE knowledge_files_fts MATCH ?
                ORDER BY bm25(knowledge_files_fts)
                LIMIT 1
                """, (keyword,))
                
                match = cursor.fetchone()
                if match:
                    file_id, title, kb_name, file_type, snippet = match
                    print(f"     最佳匹配: ID:{file_id} '{title[:30]}...'")
                    print(f"     知识库: {kb_name}, 类型: {file_type}")
                    if snippet:
                        print(f"     摘要: {snippet[:50]}...")
        except Exception as e:
            error_msg = str(e)
            if "no such function" in error_msg:
                print(f"   搜索'{keyword}': FTS函数未启用")
            else:
                print(f"   搜索'{keyword}'失败: {error_msg[:50]}")
    
    print("\n5. 检查数据质量问题...")
    
    # 检查空内容
    cursor.execute("SELECT COUNT(*) FROM knowledge_files_fts WHERE content IS NULL OR content = ''")
    empty_content = cursor.fetchone()[0]
    print(f"   空内容记录数: {empty_content}")
    
    if empty_content > 0:
        print(f"   ⚠️ 注意: 有 {empty_content} 条记录内容为空")
        print(f"     这些文件将无法被全文搜索到")
    
    # 检查标题长度
    cursor.execute("SELECT AVG(LENGTH(title)) FROM knowledge_files_fts")
    avg_title_len = cursor.fetchone()[0]
    print(f"   平均标题长度: {avg_title_len:.1f} 字符")
    
    # 检查内容长度
    cursor.execute("SELECT AVG(LENGTH(content)) FROM knowledge_files_fts WHERE content IS NOT NULL AND content != ''")
    avg_content_len = cursor.fetchone()[0]
    print(f"   平均内容长度: {avg_content_len:.1f} 字符")
    
    # 提交更改
    conn.commit()
    print("\n6. 更改已提交到数据库")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("FTS索引重建完成")
    print("=" * 60)
    
except Exception as e:
    print(f"重建失败: {e}")
    import traceback
    traceback.print_exc()