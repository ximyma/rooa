#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能服务办公平台 - 项目初始化脚本
首次运行时自动创建必要的目录和配置
"""
import os
import secrets
from pathlib import Path


def create_directories():
    """创建必要的目录结构"""
    directories = [
        'uploads',
        'uploads/proofread',
        'uploads/suggestion',
        'uploads/audio',
        'uploads/pdf',
        'uploads/chat',
        'uploads/knowledge',
        'uploads/shared',
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {directory}")


def create_env_file():
    """创建 .env 配置文件"""
    env_file = Path('.env')
    if not env_file.exists():
        secret_key = secrets.token_hex(32)
        env_content = f"""# Flask 安全配置
SECRET_KEY={secret_key}

# 数据库配置
DATABASE_URL=sqlite:///oa.db

# 上传配置（16MB）
MAX_CONTENT_LENGTH=16777216

# 日志级别（DEBUG, INFO, WARNING, ERROR）
LOG_LEVEL=INFO
"""
        env_file.write_text(env_content, encoding='utf-8')
        print(f"✓ 创建环境配置文件: .env")
        print(f"  SECRET_KEY: {secret_key[:16]}...")
    else:
        print("✓ 环境配置文件已存在")


def check_dependencies():
    """检查必要的依赖"""
    required_packages = [
        'Flask',
        'Flask-SQLAlchemy',
        'Flask-Login',
        'Flask-WTF',
        'Werkzeug',
        'python-docx',
        'PyPDF2',
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print("\n⚠ 缺少以下依赖包:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\n请运行以下命令安装依赖:")
        print("  pip install -r requirements.txt")
        return False
    
    print("✓ 所有依赖包已安装")
    return True


def main():
    print("=" * 50)
    print("智能服务办公平台 - 项目初始化")
    print("=" * 50)
    print()
    
    # 创建目录
    create_directories()
    print()
    
    # 创建环境配置
    create_env_file()
    print()
    
    # 检查依赖
    deps_ok = check_dependencies()
    print()
    
    if deps_ok:
        print("=" * 50)
        print("✓ 初始化完成！")
        print("=" * 50)
        print("\n启动项目:")
        print("  python app.py")
        print("\n访问地址:")
        print("  http://127.0.0.1:5000")
        print("\n默认账号:")
        print("  用户名: admin")
        print("  密码: admin123")
    else:
        print("=" * 50)
        print("⚠ 请先安装缺失的依赖包")
        print("=" * 50)


if __name__ == '__main__':
    main()
