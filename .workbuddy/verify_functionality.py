#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证知识库和档案管理功能
"""

import os
import sys
import sqlite3
from pathlib import Path

# 添加到Python路径
base_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(base_dir))

print("=" * 60)
print("验证OOA知识库和档案管理功能")
print("=" * 60)

def check_database():
    """检查数据库表结构"""
    db_path = base_dir / "instance" / "knowledge_base.db"
    
    if not db_path.exists():
        print(f"[✗] 数据库文件不存在: {db_path}")
        return
    
    print(f"[✓] 数据库文件存在: {db_path}")
    print(f"    文件大小: {db_path.stat().st_size:,} 字节")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"\n数据库中共有 {len(tables)} 个表:")
        knowledge_tables = []
        for table in tables:
            table_name = table[0]
            if 'knowledge' in table_name.lower() or 'fts' in table_name.lower() or 'archive' in table_name.lower():
                knowledge_tables.append(table_name)
                print(f"  [*] {table_name}")
            else:
                print(f"      {table_name}")
        
        # 检查knowledge_files表
        if 'knowledge_files' in tables:
            print(f"\n检查knowledge_files表:")
            cursor.execute("SELECT COUNT(*) FROM knowledge_files")
            count = cursor.fetchone()[0]
            print(f"    记录数: {count}")
            
            if count > 0:
                cursor.execute("SELECT file_name, file_size, file_type, LENGTH(extracted_text) as text_len, keywords, upload_time FROM knowledge_files ORDER BY upload_time DESC LIMIT 3")
                recent_files = cursor.fetchall()
                print(f"    最近 {len(recent_files)} 条记录:")
                for i, (file_name, file_size, file_type, text_len, keywords, upload_time) in enumerate(recent_files, 1):
                    print(f"    记录 {i}:")
                    print(f"      文件名: {file_name}")
                    print(f"      文件大小: {file_size:,} 字节")
                    print(f"      文件类型: {file_type}")
                    print(f"      提取文本长度: {text_len:,} 字符")
                    print(f"      关键词: {keywords[:50] if keywords else '无'}")
                    print(f"      上传时间: {upload_time}")
        
        # 检查FTS表
        if 'knowledge_files_fts' in tables:
            print(f"\n检查FTS全文索引表 (knowledge_files_fts):")
            cursor.execute("SELECT COUNT(*) FROM knowledge_files_fts")
            fts_count = cursor.fetchone()[0]
            print(f"    FTS索引记录数: {fts_count}")
            
            # 检查FTS性能
            if fts_count > 0:
                cursor.execute("SELECT COUNT(*) FROM knowledge_files_fts WHERE knowledge_files_fts MATCH '测试'")
                match_count = cursor.fetchone()[0]
                print(f"    包含'测试'的记录数: {match_count}")
                
                # 尝试复杂查询
                try:
                    cursor.execute("""
                    SELECT snippet(knowledge_files_fts, 0, '<b>', '</b>', '...', 5) as snippet, rank 
                    FROM knowledge_files_fts 
                    WHERE knowledge_files_fts MATCH '测试 OR 文档' 
                    ORDER BY rank 
                    LIMIT 3
                    """)
                    results = cursor.fetchall()
                    if results:
                        print(f"    FTS查询示例结果:")
                        for snippet, rank in results:
                            print(f"      摘要: {snippet[:100]}..., 得分: {rank:.2f}")
                except Exception as e:
                    print(f"    FTS查询测试失败: {e}")
        
        # 检查档案相关表
        archive_tables = [t for t in tables if 'archive' in t.lower()]
        if archive_tables:
            print(f"\n检查档案相关表 ({len(archive_tables)} 个):")
            for table in archive_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"    {table}: {count} 条记录")
        
        conn.close()
        print("\n[✓] 数据库检查完成")
        
    except Exception as e:
        print(f"[✗] 数据库检查失败: {e}")

def check_smart_knowledge():
    """检查智能知识库功能"""
    print(f"\n检查智能知识库功能:")
    
    try:
        # 导入smart_knowledge模块
        from smart_knowledge import extract_text, extract_keywords, _get_embedding_model
        
        # 创建测试文件
        test_content = "这是一个用于测试智能知识库功能的文档。文档包含人工智能、机器学习、深度学习等关键词。希望系统能正确提取文本和关键词。"
        
        test_file = base_dir / "test_temp.txt"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)
        
        print(f"[✓] 创建测试文件: {test_file}")
        
        # 测试文本提取
        try:
            extracted = extract_text(str(test_file))
            print(f"[✓] 文本提取功能正常")
            print(f"    提取文本长度: {len(extracted)} 字符")
            print(f"    前50字符: {extracted[:50]}...")
        except Exception as e:
            print(f"[✗] 文本提取失败: {e}")
        
        # 测试关键词提取
        try:
            keywords = extract_keywords(test_content)
            print(f"[✓] 关键词提取功能正常")
            print(f"    提取关键词: {', '.join(keywords) if keywords else '无'}")
        except Exception as e:
            print(f"[✗] 关键词提取失败: {e}")
        
        # 测试BERT模型
        try:
            model = _get_embedding_model()
            if model:
                print(f"[✓] BERT模型加载正常")
                # 测试嵌入
                embedding = model.encode("测试句子")
                print(f"    嵌入维度: {embedding.shape}")
                print(f"    示例嵌入值: {embedding[:3]}")
            else:
                print(f"[✗] BERT模型未加载")
        except Exception as e:
            print(f"[✗] BERT模型检查失败: {e}")
        
        # 清理测试文件
        try:
            test_file.unlink()
            print(f"[✓] 清理测试文件")
        except:
            pass
            
    except ImportError as e:
        print(f"[✗] 导入smart_knowledge模块失败: {e}")
    except Exception as e:
        print(f"[✗] 检查智能知识库功能失败: {e}")

def check_app_routes():
    """检查应用路由"""
    print(f"\n检查应用路由:")
    
    try:
        # 导入应用
        from app import app
        
        routes = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint.startswith(('knowledge_', 'archive_', 'file_')):
                routes.append((rule.rule, rule.endpoint, rule.methods))
        
        print(f"找到 {len(routes)} 个知识库/档案/文件相关路由:")
        
        knowledge_routes = [r for r in routes if r[1].startswith('knowledge_')]
        archive_routes = [r for r in routes if r[1].startswith('archive_')]
        file_routes = [r for r in routes if r[1].startswith('file_')]
        
        if knowledge_routes:
            print(f"\n知识库路由 ({len(knowledge_routes)} 个):")
            for route, endpoint, methods in knowledge_routes[:10]:  # 只显示前10个
                print(f"  {endpoint:30s} {route:40s} {methods}")
        
        if archive_routes:
            print(f"\n档案管理路由 ({len(archive_routes)} 个):")
            for route, endpoint, methods in archive_routes[:10]:
                print(f"  {endpoint:30s} {route:40s} {methods}")
        
        if file_routes:
            print(f"\n文件上传路由 ({len(file_routes)} 个):")
            for route, endpoint, methods in file_routes:
                print(f"  {endpoint:30s} {route:40s} {methods}")
        
        print("\n[✓] 路由检查完成")
        
    except Exception as e:
        print(f"[✗] 路由检查失败: {e}")

def check_uploads_directory():
    """检查上传目录"""
    print(f"\n检查上传目录:")
    
    uploads_dir = base_dir / "uploads"
    
    if uploads_dir.exists():
        print(f"[✓] 上传目录存在: {uploads_dir}")
        
        # 列出子目录
        subdirs = [d for d in uploads_dir.iterdir() if d.is_dir()]
        files = [f for f in uploads_dir.iterdir() if f.is_file()]
        
        print(f"    子目录数: {len(subdirs)}")
        print(f"    文件数: {len(files)}")
        
        if subdirs:
            print("    子目录列表:")
            for d in subdirs:
                dir_files = list(d.glob("*"))
                print(f"      - {d.name}: {len(dir_files)} 个文件")
                
    else:
        print(f"[✗] 上传目录不存在: {uploads_dir}")
        print("    尝试创建上传目录...")
        try:
            uploads_dir.mkdir(parents=True, exist_ok=True)
            print(f"[✓] 已创建上传目录: {uploads_dir}")
        except Exception as e:
            print(f"[✗] 创建上传目录失败: {e}")

if __name__ == "__main__":
    check_database()
    check_smart_knowledge()
    check_app_routes()
    check_uploads_directory()
    
    print("\n" + "=" * 60)
    print("功能验证完成")
    print("=" * 60)