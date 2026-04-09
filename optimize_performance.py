#!/usr/bin/env python3
"""
智能OA系统性能优化脚本
此脚本应用数据库索引和其他性能优化
"""

import os
import sys
import sqlite3
from pathlib import Path

def create_indexes():
    """为现有数据库创建索引"""
    db_path = Path(__file__).parent / 'oa.db'
    if not db_path.exists():
        print("数据库文件不存在，将在首次运行时自动创建索引")
        return
    
    print(f"正在为数据库 {db_path} 创建索引...")
    
    # SQLite 连接
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 获取现有索引
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    existing_indexes = {row[0] for row in cursor.fetchall()}
    
    # 需要创建的索引列表（从models.py定义的索引）
    indexes = [
        # User 表
        ("idx_user_department", "users", "department"),
        ("idx_user_role", "users", "role"),
        
        # KnowledgeBase 表
        ("idx_kb_owner_type", "knowledge_bases", "owner_id, type"),
        ("idx_kb_type_public", "knowledge_bases", "type, is_public"),
        ("idx_kb_owner", "knowledge_bases", "owner_id"),
        
        # KnowledgeFile 表
        ("idx_kf_kb_id", "knowledge_files", "knowledge_base_id"),
        ("idx_kf_kb_id_status", "knowledge_files", "knowledge_base_id, status"),
        ("idx_kf_uploaded_by", "knowledge_files", "uploaded_by"),
        ("idx_kf_status", "knowledge_files", "status"),
        
        # SpecialReport 表
        ("idx_sr_reporter_id", "special_reports", "reporter_id"),
        ("idx_sr_reporter_status", "special_reports", "reporter_id, status"),
        ("idx_sr_status", "special_reports", "status"),
        ("idx_sr_updated_at", "special_reports", "updated_at"),
        ("idx_sr_target_department", "special_reports", "target_department"),
        ("idx_sr_reporter_updated", "special_reports", "reporter_id, updated_at"),
        
        # AssignmentTask 表
        ("idx_task_status", "assignment_tasks", "status"),
        ("idx_task_created_by", "assignment_tasks", "created_by"),
        ("idx_task_end_time", "assignment_tasks", "end_time"),
        ("idx_task_status_created", "assignment_tasks", "status, created_at"),
        
        # TaskSubmission 表
        ("idx_submission_task_user", "task_submissions", "task_id, user_id"),
        ("idx_submission_user_status", "task_submissions", "user_id, status"),
        ("idx_submission_task", "task_submissions", "task_id"),
        ("idx_submission_user", "task_submissions", "user_id"),
        
        # AIModelConfig 表
        ("idx_aimc_is_active", "ai_model_configs", "is_active"),
        ("idx_aimc_provider", "ai_model_configs", "provider"),
        
        # ChatSession 表
        ("idx_chatsession_user_id", "chat_sessions", "user_id"),
        ("idx_chatsession_updated_at", "chat_sessions", "updated_at"),
        ("idx_chatsession_user_updated", "chat_sessions", "user_id, updated_at"),
        
        # ChatMessage 表
        ("idx_chatmsg_session_id", "chat_messages", "session_id"),
        ("idx_chatmsg_created_at", "chat_messages", "created_at"),
        ("idx_chatmsg_session_created", "chat_messages", "session_id, created_at"),
    ]
    
    created_count = 0
    for idx_name, table, columns in indexes:
        if idx_name in existing_indexes:
            print(f"  索引 {idx_name} 已存在，跳过")
            continue
        
        try:
            sql = f"CREATE INDEX {idx_name} ON {table} ({columns})"
            cursor.execute(sql)
            print(f"  创建索引: {idx_name} ON {table}({columns})")
            created_count += 1
        except sqlite3.Error as e:
            print(f"  创建索引 {idx_name} 失败: {e}")
    
    conn.commit()
    conn.close()
    print(f"索引创建完成，共创建了 {created_count} 个新索引")

def install_dependencies():
    """安装性能优化依赖"""
    print("安装性能优化依赖...")
    os.system("pip install Flask-Caching==2.3.1")
    print("依赖安装完成")

def main():
    print("=" * 60)
    print("智能OA系统性能优化工具")
    print("=" * 60)
    
    # 检查是否在虚拟环境中
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("警告：建议在虚拟环境中运行此脚本")
    
    print("\n1. 安装依赖...")
    install_dependencies()
    
    print("\n2. 创建数据库索引...")
    create_indexes()
    
    print("\n" + "=" * 60)
    print("优化完成！")
    print("=" * 60)
    print("\n优化内容：")
    print("  [OK] 数据库索引 - 加速查询性能")
    print("  [OK] 路由缓存 - 首页等频繁访问页面缓存5分钟")
    print("  [OK] 静态文件缓存 - 静态资源缓存1年")
    print("  [OK] 查询优化 - 待办事项查询优化")
    print("\n使用说明：")
    print("  1. 重启应用以使优化生效")
    print("  2. 运行 start.bat 或 python app.py")
    print("  3. 首次访问可能稍慢（缓存未命中），后续访问会显著加快")
    print("\n注意事项：")
    print("  - 缓存会在数据更新时自动清除")
    print("  - 如需清除所有缓存，重启应用即可")
    print("  - 生产环境建议使用Redis作为缓存后端")

if __name__ == '__main__':
    main()