"""
OA系统配置管理模块
支持智能知识库、OCR、嵌入模型等配置
"""

import os
import json
from datetime import datetime

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'system_config.json')

# 默认配置
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
        "enabled": True,
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


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    # 合并默认配置和保存的配置
                    config = DEFAULT_CONFIG.copy()
                    self._deep_update(config, saved_config)
                    return config
            except Exception as e:
                print(f"[错误] 加载配置失败: {e}")
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()
    
    def _deep_update(self, d, u):
        """深度更新字典"""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                d[k] = self._deep_update(d[k], v)
            else:
                d[k] = v
        return d
    
    def save_config(self):
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[错误] 保存配置失败: {e}")
            return False
    
    def get(self, key_path, default=None):
        """
        获取配置值
        key_path: 点分隔的路径，如 "knowledge_base.embedding_model_path"
        """
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path, value):
        """
        设置配置值
        key_path: 点分隔的路径
        """
        keys = key_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        return self.save_config()
    
    def update_section(self, section, values):
        """更新整个配置节"""
        if section in self.config:
            self.config[section].update(values)
        else:
            self.config[section] = values
        return self.save_config()
    
    def get_all(self):
        """获取所有配置"""
        return self.config
    
    def reset_to_default(self):
        """重置为默认配置"""
        self.config = DEFAULT_CONFIG.copy()
        return self.save_config()
    
    # ========== 快捷方法 ==========
    
    def get_embedding_model_path(self):
        """获取嵌入模型路径"""
        path = self.get('knowledge_base.embedding_model_path')
        if not os.path.isabs(path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, path)
        return path
    
    def get_tesseract_cmd(self):
        """获取Tesseract命令路径"""
        return self.get('ocr.tesseract_cmd')
    
    def get_tessdata_dir(self):
        """获取Tessdata目录"""
        return self.get('ocr.tessdata_dir')
    
    def is_ocr_enabled(self):
        """OCR是否启用"""
        return self.get('ocr.enabled', True)
    
    def get_ocr_languages(self):
        """获取OCR语言列表"""
        langs = self.get('ocr.languages', ['chi_sim', 'eng'])
        return '+'.join(langs)


# 全局配置实例
config_manager = ConfigManager()
