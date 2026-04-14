import os
import secrets
from pathlib import Path


class Config:
    # 安全密钥 - 必须使用固定值，否则每次重启session失效，CSRF报错
    SECRET_KEY = 'ooa-secret-key-2026-fixed-do-not-change'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///oa.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 上传文件配置
    BASE_DIR = Path(__file__).resolve().parent
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 1024 * 1024 * 1024))  # 默认 1GB
    
    # 文本内容提取配置（默认值，实际从系统配置管理器获取）
    MAX_EXTRACTED_TEXT_LENGTH = -1  # -1表示无限制，实际值从系统配置获取
    MAX_PREVIEW_LENGTH = 100000  # 预览页面最大字符数
    MAX_AI_SAMPLE_LENGTH = 5000  # AI分析使用最大字符数
    MAX_FILE_PREVIEW_LENGTH = 50000  # 文件预览最大字符数
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'mp3', 'wav', 'mp4', 'avi', 'mov',
        'jpg', 'png', 'jpeg', 'gif', 'bmp', 'tiff',
        'zip', 'rar', '7z', 'gz', 'tar',
        'csv', 'md', 'html', 'htm'
    }
    
    # SQLite 性能优化配置
    SQLITE_PRAGMAS = {
        'synchronous': 'NORMAL',
        'journal_mode': 'WAL',
        'cache_size': -10000,  # 负数表示 KB，-10000 = 10MB
        'temp_store': 'MEMORY',
    }

    # 缓存配置 - 使用内存缓存，生产环境可改用Redis
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300  # 5分钟
    CACHE_THRESHOLD = 1000  # 最大缓存条目数

    # WTForms CSRF - 公网访问时需允许来自不同 Host 的请求
    WTF_CSRF_SSL_STRICT = False
    # SESSION_COOKIE_SECURE = True  # 若部署了 HTTPS，取消此注释
    # Session 有效期（秒）- 默认7天
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('SESSION_LIFETIME', 7 * 24 * 3600))