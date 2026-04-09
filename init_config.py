"""
初始化系统配置文件
运行此脚本创建默认配置
"""

import os
import json

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'system_config.json')

DEFAULT_CONFIG = {
    "knowledge_base": {
        "embedding_model_path": "models/all-MiniLM-L6-v2",
        "use_local_model": True,
        "max_file_size_mb": 50,
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
        "max_extracted_length": -1,  # -1表示无限制，其他值表示最大字符数
        "max_preview_length": 100000,  # 预览页面最大字符数
        "max_ai_sample_length": 5000,  # AI分析使用最大字符数
        "max_file_preview_length": 50000,  # 文件预览最大字符数
        "max_upload_size_mb": 1024  # 最大上传文件大小(MB)
    }
}

def init_config():
    """初始化配置文件"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    if os.path.exists(CONFIG_FILE):
        print(f"[信息] 配置文件已存在: {CONFIG_FILE}")
        print("[信息] 如需重置，请删除该文件后重新运行")
        return
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
    
    print(f"[成功] 配置文件已创建: {CONFIG_FILE}")
    print("\n默认配置:")
    print(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    init_config()
