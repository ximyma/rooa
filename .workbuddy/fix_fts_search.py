#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复FTS搜索问题
"""

import os
import sys
import sqlite3
from pathlib import Path

base_dir = Path(__file__).parent.parent.absolute()
db_path = base_dir / "instance" / "oa.db"

print("=" * 60)
print("修复FTS搜索问题")
print("=" * 60)

try:
    # 连接到数据库
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("1. 检查当前FTS索引状态:")
    
    # 检查FTS表记录数
    cursor.execute("SELECT COUNT(*) FROM knowledge_files_fts")
    fts_count = cursor.fetchone()[0]
    print(f"   FTS索引记录数: {fts_count}")
    
    # 检查源表记录数
    cursor.execute("SELECT COUNT(*) FROM knowledge_files WHERE status = 'approved'")
    approved_count = cursor.fetchone()[0]
    print(f"   已审核文件数: {approved_count}")
    
    if fts_count != approved_count:
        print(f"   ⚠️ 警告: FTS索引记录数与已审核文件数不匹配")
    
    print("\n2. 分析FTS索引内容:")
    
    # 检查FTS索引中的内容
    cursor.execute("""
    SELECT 
        COUNT(CASE WHEN content IS NULL OR content = '' THEN 1 END) as empty_content,
        COUNT(CASE WHEN content LIKE '%解析失败%' THEN 1 END) as parse_failed,
        COUNT(CASE WHEN content NOT LIKE '%解析失败%' AND content IS NOT NULL AND content != '' THEN 1 END) as valid_content
    FROM knowledge_files_fts
    """)
    
    empty_ft, failed_ft, valid_ft = cursor.fetchone()
    print(f"   空内容: {empty_ft}")
    print(f"   解析失败: {failed_ft}")
    print(f"   有效内容: {valid_ft}")
    
    print("\n3. 修复建议:")
    
    if empty_ft > 0 or failed_ft > 0:
        print(f"   🔧 建议重新构建FTS索引")
        
        # 检查是否可以手动修复一些记录
        print(f"\n4. 尝试修复FTS索引:")
        
        # 查找有content_text但FTS中内容为空或错误的记录
        cursor.execute("""
        SELECT kf.id, kf.filename, kf.file_type, kf.content_text, fts.content as fts_content
        FROM knowledge_files kf
        LEFT JOIN knowledge_files_fts fts ON kf.id = fts.file_id
        WHERE kf.status = 'approved'
        AND (fts.content IS NULL OR fts.content = '' OR fts.content LIKE '%解析失败%')
        AND kf.content_text IS NOT NULL 
        AND kf.content_text != ''
        AND kf.content_text NOT LIKE '%解析失败%'
        LIMIT 10
        """)
        
        fixable_records = cursor.fetchall()
        print(f"   可以修复的记录数 (前10个): {len(fixable_records)}")
        
        for i, (file_id, filename, file_type, content_text, fts_content) in enumerate(fixable_records, 1):
            content_preview = content_text[:50].replace('\n', ' ') if content_text else ''
            fts_preview = fts_content[:50] if fts_content else ''
            print(f"   [{i}] ID:{file_id} '{filename}'")
            print(f"       文件类型: {file_type}")
            print(f"       原始内容: {content_preview}...")
            print(f"       FTS内容: {fts_preview}...")
            
            # 修复这条记录
            if content_text and content_text.strip():
                # 获取知识库信息
                cursor.execute("""
                SELECT kb.name, kb.type
                FROM knowledge_files kf
                JOIN knowledge_bases kb ON kf.knowledge_base_id = kb.id
                WHERE kf.id = ?
                """, (file_id,))
                
                kb_info = cursor.fetchone()
                kb_name = kb_info[0] if kb_info else ''
                kb_type = kb_info[1] if kb_info else ''
                
                # 获取tags
                cursor.execute("SELECT tags FROM knowledge_files WHERE id = ?", (file_id,))
                tags = cursor.fetchone()[0] if cursor.fetchone() else ''
                
                # 更新FTS记录
                title = filename[:100]  # 使用文件名作为标题
                content = content_text[:1000]  # 限制内容长度
                
                cursor.execute("""
                DELETE FROM knowledge_files_fts WHERE file_id = ?
                """, (file_id,))
                
                cursor.execute("""
                INSERT INTO knowledge_files_fts(file_id, title, content, kb_name, kb_type, file_type, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (file_id, title, content, kb_name, kb_type, file_type, tags or ''))
                
                print(f"       ✅ 已修复FTS记录")
    
    else:
        print(f"   ✅ FTS索引内容正常")
    
    print("\n5. 测试修复后的搜索功能:")
    
    # 测试搜索
    test_keywords = ['测试', '工作', '文档', '管理']
    for keyword in test_keywords:
        try:
            cursor.execute("""
            SELECT COUNT(*)
            FROM knowledge_files_fts
            WHERE knowledge_files_fts MATCH ?
            """, (keyword,))
            
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
                
                best_match = cursor.fetchone()
                if best_match:
                    file_id, title, kb_name, file_type, snippet = best_match
                    print(f"      最佳匹配: ID:{file_id} '{title}'")
                    print(f"      知识库: {kb_name}, 类型: {file_type}")
                    print(f"      摘要: {snippet}...")
        except Exception as e:
            print(f"   搜索'{keyword}'失败: {str(e)[:50]}")
    
    # 提交更改
    conn.commit()
    print("\n6. 修复完成")
    
    print("\n7. 后续建议:")
    print(f"   a. 如果搜索结果仍然不显示，检查模板渲染逻辑")
    print(f"   b. 确保所有新上传的文件都触发FTS索引更新")
    print(f"   c. 考虑定期重建FTS索引以保持数据一致性")
    
    conn.close()
    
except Exception as e:
    print(f"修复失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("修复脚本完成")
print("=" * 60)