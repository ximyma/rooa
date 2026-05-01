#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能服务办公平台 - 系统完整初始化入口
整合所有初始化步骤,一键完成系统部署
"""
import os
import sys
import secrets
from pathlib import Path


def create_directories():
    """创建必要的目录结构"""
    print("=" * 60)
    print("1. 创建必要目录")
    print("=" * 60)
    directories = [
        'uploads',
        'uploads/proofread',
        'uploads/suggestion',
        'uploads/audio',
        'uploads/pdf',
        'uploads/chat',
        'uploads/knowledge',
        'uploads/shared',
        'uploads/archive',
        'config',
    ]
    
    created_count = 0
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            created_count += 1
            print(f"  ✓ 创建: {directory}")
        else:
            print(f"  - 已存在: {directory}")
    
    if created_count > 0:
        print(f"\n✓ 共创建 {created_count} 个目录")
    else:
        print(f"\n✓ 所有目录已存在")
    print()


def create_env_file():
    """创建环境配置文件"""
    print("=" * 60)
    print("2. 创建环境配置")
    print("=" * 60)
    env_file = Path('.env')
    if not env_file.exists():
        secret_key = secrets.token_hex(32)
        env_content = f"""# Flask 安全配置
SECRET_KEY={secret_key}

# 数据库配置
DATABASE_URL=sqlite:///oa.db

# 上传配置（100MB）
MAX_CONTENT_LENGTH=104857600

# 日志级别（DEBUG, INFO, WARNING, ERROR）
LOG_LEVEL=INFO
"""
        env_file.write_text(env_content, encoding='utf-8')
        print(f"✓ 创建 .env 配置文件")
        print(f"  SECRET_KEY: {secret_key[:20]}...")
    else:
        print("✓ .env 配置文件已存在")
    print()


def create_system_config():
    """创建系统配置JSON文件"""
    print("=" * 60)
    print("3. 创建系统配置文件")
    print("=" * 60)
    import json
    CONFIG_DIR = Path('config')
    CONFIG_FILE = CONFIG_DIR / 'system_config.json'
    
    DEFAULT_CONFIG = {
        "knowledge_base": {
            "embedding_model_path": "models/all-MiniLM-L6-v2",
            "use_local_model": True,
            "max_file_size_mb": 100,
            "batch_size": 10,
            "auto_extract_keywords": True,
            "auto_generate_summary": True,
            "auto_tag": True
        },
        "ocr": {
            "enabled": False,
            "tesseract_cmd": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
            "tessdata_dir": "C:\\Program Files\\Tesseract-OCR\\tessdata",
            "languages": ["chi_sim", "eng"],
            "dpi": 300,
            "psm_mode": 6
        },
        "ai": {
            "default_model": "deepseek",
            "temperature": 0.7,
            "max_tokens": 2000
        },
        "monitoring": {
            "auto_run": True,
            "check_interval_hours": 24,
            "notify_on_overdue": True
        },
        "document": {
            "max_extracted_length": -1,
            "max_preview_length": 100000,
            "max_ai_sample_length": 5000,
            "max_file_preview_length": 50000,
            "max_upload_size_mb": 100
        }
    }
    
    if not CONFIG_FILE.exists():
        CONFIG_DIR.mkdir(exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        print(f"✓ 创建 system_config.json 配置文件")
    else:
        print(f"✓ system_config.json 配置文件已存在")
    print()


def init_database():
    """初始化数据库"""
    print("=" * 60)
    print("4. 初始化数据库")
    print("=" * 60)
    print()
    
    try:
        from init_db_standalone import main as init_db_main
        success = init_db_main()
        return success
    except ImportError:
        print("✗ 无法导入 init_db_standalone 模块")
        return False
    except Exception as e:
        print(f"✗ 数据库初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_dependencies():
    """检查依赖包"""
    print("=" * 60)
    print("5. 检查依赖包")
    print("=" * 60)
    required_packages = [
        ('Flask', 'flask'),
        ('Flask-SQLAlchemy', 'flask_sqlalchemy'),
        ('Flask-Login', 'flask_login'),
        ('Flask-WTF', 'flask_wtf'),
        ('Werkzeug', 'werkzeug'),
        ('python-docx', 'docx'),
        ('PyPDF2', 'PyPDF2'),
    ]
    
    missing = []
    for package_name, module_name in required_packages:
        try:
            __import__(module_name)
            print(f"  ✓ {package_name}")
        except ImportError:
            missing.append(package_name)
            print(f"  ✗ {package_name} (缺失)")
    
    if missing:
        print(f"\n⚠  缺少 {len(missing)} 个依赖包")
        print("\n请运行以下命令安装依赖:")
        print("  pip install -r requirements.txt")
        return False
    else:
        print(f"\n✓ 所有依赖包已安装")
        return True
    print()


def show_summary():
    """显示初始化总结"""
    print("=" * 60)
    print("系统初始化完成!")
    print("=" * 60)
    print()
    print("系统信息:")
    print("  - 系统名称: 智能服务办公平台")
    print("  - 数据库: SQLite (oa.db)")
    print()
    print("快速开始:")
    print("  1. 启动系统: python app.py")
    print("  2. 访问地址: http://127.0.0.1:5000")
    print()
    print("默认登录账号:")
    print("  用户名: admin")
    print("  密码: admin123")
    print()
    print("⚠ 重要提醒: 请在首次登录后立即修改默认密码!")
    print()


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 8 + "智能服务办公平台 - 系统完整初始化" + " " * 8 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        # 切换到脚本所在目录
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        
        # 执行所有初始化步骤
        create_directories()
        create_env_file()
        create_system_config()
        db_success = init_database()
        dep_success = check_dependencies()
        
        # 显示总结
        show_summary()
        
        if not db_success:
            print("\n⚠ 数据库初始化存在问题,请检查上述错误信息")
            return False
        if not dep_success:
            print("\n⚠ 依赖包不完整,请先安装缺失的依赖包")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n✗ 系统初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
