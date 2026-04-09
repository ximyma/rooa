#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试知识库文件上传、文本提取、关键词生成功能
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_upload_and_extract():
    """测试文件上传和文本提取功能"""
    print("=" * 60)
    print("测试知识库文件上传、文本提取、关键词生成功能")
    print("=" * 60)
    
    # 创建测试目录
    test_dir = Path(tempfile.mkdtemp(prefix="ooa_test_"))
    print(f"创建测试目录: {test_dir}")
    
    # 创建测试文件
    test_file = test_dir / "test_doc.txt"
    test_content = """这是一个测试文档。
用于验证OOA知识库的文件上传、文本提取和关键词生成功能。
文档内容包含：人工智能、机器学习、自然语言处理、深度学习等关键词。
希望系统能正确提取文本内容和生成关键词。"""
    
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    print(f"创建测试文件: {test_file}")
    print(f"文件大小: {os.path.getsize(test_file)} 字节")
    
    # 导入应用模块
    try:
        from app import app, db
        from models import KnowledgeFile
        from smart_knowledge import extract_text, extract_keywords
        
        print("\n[✓] 成功导入应用模块")
        
        # 在应用上下文中运行
        with app.app_context():
            print("\n1. 测试文本提取功能...")
            
            # 模拟文件上传
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 测试extract_text函数
            try:
                extracted_text = extract_text(str(test_file))
                print(f"[✓] 文本提取成功")
                print(f"  提取前长度: {len(content)} 字符")
                print(f"  提取后长度: {len(extracted_text)} 字符")
                if len(extracted_text) > 0:
                    print(f"  [✓] 成功提取到文本内容")
                    print(f"  示例内容: {extracted_text[:100]}...")
                else:
                    print(f"  [✗] 提取到的文本为空")
            except Exception as e:
                print(f"[✗] 文本提取失败: {e}")
            
            print("\n2. 测试关键词提取功能...")
            try:
                if extracted_text and len(extracted_text) > 0:
                    keywords = extract_keywords(extracted_text)
                    print(f"✓ 关键词提取成功")
                    print(f"  提取到 {len(keywords)} 个关键词")
                    if keywords:
                        print(f"  关键词列表: {', '.join(keywords)}")
                    else:
                        print(f"  [✗] 未提取到关键词")
                else:
                    print(f"[✗] 跳过关键词提取: 文本为空")
            except Exception as e:
                print(f"[✗] 关键词提取失败: {e}")
            
            print("\n3. 检查BERT嵌入模型...")
            try:
                from smart_knowledge import _get_embedding_model
                model = _get_embedding_model()
                if model:
                    print(f"[✓] BERT模型加载成功")
                    
                    # 测试嵌入生成
                    test_sentence = "这是一个测试句子"
                    try:
                        embedding = model.encode(test_sentence)
                        print(f"[✓] 嵌入生成成功")
                        print(f"  嵌入维度: {embedding.shape}")
                        print(f"  示例嵌入[:5]: {embedding[:5]}")
                    except Exception as e:
                        print(f"[✗] 嵌入生成失败: {e}")
                else:
                    print(f"[✗] BERT模型未加载")
            except Exception as e:
                print(f"[✗] 检查BERT模型时出错: {e}")
            
            print("\n4. 检查知识库数据库表...")
            try:
                from sqlalchemy import inspect
                
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                
                knowledge_tables = [t for t in tables if 'knowledge' in t.lower() or 'fts' in t.lower()]
                print(f"找到 {len(knowledge_tables)} 个知识库相关表:")
                for table in knowledge_tables:
                    print(f"  - {table}")
                
                # 检查knowledge_files表
                if 'knowledge_files' in tables:
                    count = db.session.query(KnowledgeFile).count()
                    print(f"\n当前knowledge_files表中有 {count} 条记录")
                    
                    if count > 0:
                        # 查看最新记录
                        latest = db.session.query(KnowledgeFile).order_by(KnowledgeFile.upload_time.desc()).first()
                        print(f"最新记录:")
                        print(f"  文件名: {latest.file_name}")
                        print(f"  存储路径: {latest.file_path}")
                        print(f"  文件类型: {latest.file_type}")
                        print(f"  文件大小: {latest.file_size}")
                        print(f"  提取文本长度: {len(latest.extracted_text) if latest.extracted_text else 0}")
                        print(f"  关键词: {latest.keywords}")
                        print(f"  上传时间: {latest.upload_time}")
                    else:
                        print("knowledge_files表中无记录")
                else:
                    print("knowledge_files表不存在")
                    
            except Exception as e:
                print(f"[✗] 检查数据库表时出错: {e}")
            
            print("\n5. 测试FTS全文检索...")
            try:
                from app import search_knowledge_fts
                
                test_keywords = ["测试", "人工智能", "机器学习"]
                for keyword in test_keywords:
                    print(f"\n  搜索关键词: '{keyword}'")
                    results = search_knowledge_fts(keyword, limit=5)
                    print(f"  找到 {len(results)} 条结果")
                    
                    if results:
                        for i, (kf, score) in enumerate(results[:3], 1):
                            print(f"    结果 {i}: 文件名={kf.file_name}, 文件大小={kf.file_size} bytes, FTS分数={score:.2f}")
                
            except Exception as e:
                print(f"[✗] 测试FTS检索时出错: {e}")
            
    except ImportError as e:
        print(f"[✗] 导入模块失败: {e}")
    except Exception as e:
        print(f"[✗] 测试过程中发生错误: {e}")
    
    # 清理测试目录
    try:
        shutil.rmtree(test_dir)
        print(f"\n清理测试目录: {test_dir}")
    except:
        pass
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_upload_and_extract()