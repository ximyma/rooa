#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单验证知识库和档案管理功能
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

def check_system_status():
    """检查系统状态"""
    print("\n[1] 检查系统状态:")
    
    # 检查数据库
    db_path = base_dir / "instance" / "knowledge_base.db"
    if db_path.exists():
        print(f"   数据库文件: 存在 ({db_path.stat().st_size:,} 字节)")
    else:
        print(f"   数据库文件: 不存在")
        return False
    
    # 检查上传目录
    uploads_dir = base_dir / "uploads"
    if uploads_dir.exists():
        print(f"   上传目录: 存在")
    else:
        print(f"   上传目录: 不存在")
        # 尝试创建
        try:
            uploads_dir.mkdir(parents=True, exist_ok=True)
            print(f"   已创建上传目录")
        except:
            print(f"   创建上传目录失败")
    
    return True

def check_knowledge_files():
    """检查知识库文件"""
    print("\n[2] 检查知识库文件表:")
    
    try:
        conn = sqlite3.connect(str(base_dir / "instance" / "knowledge_base.db"))
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_files';")
        if cursor.fetchone():
            print(f"   knowledge_files表: 存在")
            
            # 统计记录
            cursor.execute("SELECT COUNT(*) FROM knowledge_files")
            count = cursor.fetchone()[0]
            print(f"   记录数: {count}")
            
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
                
                print(f"   有提取文本的记录: {has_text}/{total} ({has_text/total*100:.1f}%)")
                print(f"   有关键词的记录: {has_keywords}/{total} ({has_keywords/total*100:.1f}%)")
                
                # 查看最新记录
                cursor.execute("""
                SELECT file_name, file_type, file_size, 
                       LENGTH(extracted_text) as text_len, keywords,
                       upload_time
                FROM knowledge_files 
                ORDER BY upload_time DESC 
                LIMIT 3
                """)
                
                rows = cursor.fetchall()
                if rows:
                    print(f"   最近3条记录:")
                    for i, (name, ftype, size, text_len, keywords, upload_time) in enumerate(rows, 1):
                        print(f"     [{i}] {name} ({ftype}, {size:,} 字节)")
                        print(f"         文本长度: {text_len:,} 字符")
                        print(f"         关键词: {keywords[:50] if keywords else '无'}")
                        print(f"         上传时间: {upload_time}")
            else:
                print(f"   表中无记录")
        else:
            print(f"   knowledge_files表: 不存在")
        
        # 检查FTS表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_files_fts';")
        if cursor.fetchone():
            print(f"\n   FTS全文索引表: 存在")
            
            cursor.execute("SELECT COUNT(*) FROM knowledge_files_fts")
            fts_count = cursor.fetchone()[0]
            print(f"   FTS索引记录数: {fts_count}")
            
            # 测试FTS查询
            try:
                cursor.execute("SELECT COUNT(*) FROM knowledge_files_fts WHERE knowledge_files_fts MATCH '测试'")
                test_count = cursor.fetchone()[0]
                print(f"   包含'测试'的记录: {test_count}")
            except:
                print(f"   FTS查询测试失败")
        else:
            print(f"\n   FTS全文索引表: 不存在")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   检查失败: {e}")
        return False

def test_extract_functions():
    """测试提取函数"""
    print("\n[3] 测试提取函数:")
    
    try:
        # 创建测试文件
        test_file = base_dir / "test_simple.txt"
        test_content = "这是一个测试文档，用于验证文本提取和关键词生成功能。人工智能和机器学习是当前热门技术。"
        
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_content)
        
        print(f"   创建测试文件: {test_file}")
        
        # 测试文本提取
        try:
            from smart_knowledge import extract_text, extract_keywords
            
            extracted = extract_text(str(test_file))
            print(f"   文本提取测试: 成功")
            print(f"      提取长度: {len(extracted)} 字符")
            print(f"      内容示例: {extracted[:50]}...")
            
            # 测试关键词提取
            keywords = extract_keywords(test_content)
            print(f"   关键词提取测试: 成功")
            print(f"      提取关键词: {', '.join(keywords) if keywords else '无'}")
            
        except ImportError:
            print(f"   导入smart_knowledge模块失败")
        except Exception as e:
            print(f"   提取测试失败: {e}")
        
        # 清理测试文件
        try:
            test_file.unlink()
            print(f"   已清理测试文件")
        except:
            pass
            
    except Exception as e:
        print(f"   测试准备失败: {e}")

def check_bert_model():
    """检查BERT模型"""
    print("\n[4] 检查BERT模型:")
    
    try:
        from smart_knowledge import _get_embedding_model
        
        model = _get_embedding_model()
        if model:
            print(f"   BERT模型: 已加载")
            
            # 测试嵌入
            test_text = "这是一个测试句子"
            embedding = model.encode(test_text)
            print(f"   嵌入测试: 成功")
            print(f"      句子: '{test_text}'")
            print(f"      维度: {embedding.shape}")
            print(f"      示例值: {embedding[:3]}")
        else:
            print(f"   BERT模型: 未加载")
            
    except ImportError:
        print(f"   导入smart_knowledge模块失败")
    except Exception as e:
        print(f"   模型检查失败: {e}")

def check_upload_routes():
    """检查上传路由"""
    print("\n[5] 检查上传路由:")
    
    try:
        from app import app
        
        upload_routes = []
        for rule in app.url_map.iter_rules():
            if 'upload' in rule.rule.lower() or 'file_' in rule.endpoint:
                upload_routes.append(rule)
        
        print(f"   找到 {len(upload_routes)} 个上传相关路由:")
        
        for i, rule in enumerate(upload_routes[:5], 1):
            print(f"     [{i}] {rule.endpoint}: {rule.rule}")
            
            # 检查方法
            methods = list(rule.methods - {'HEAD', 'OPTIONS'})
            if methods:
                print(f"         方法: {', '.join(methods)}")
                
    except Exception as e:
        print(f"   路由检查失败: {e}")

if __name__ == "__main__":
    print(f"工作目录: {base_dir}")
    
    if check_system_status():
        check_knowledge_files()
        test_extract_functions()
        check_bert_model()
        check_upload_routes()
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)