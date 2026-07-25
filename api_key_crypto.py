"""
API Key 加密存储模块
使用 Fernet 对称加密保护数据库中的 API Key
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 默认盐值（公开，仅用于派生密钥，不增加安全性但避免裸 key）
_DEFAULT_SALT = b'ooa-api-key-salt-v1\x00\x00\x00\x00'
_fernet_instance = None
_master_key = None


def _derive_key(master_key: str, salt: bytes = None) -> bytes:
    """从主密钥派生 Fernet 兼容的 32 字节密钥"""
    if salt is None:
        salt = _DEFAULT_SALT
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_key.encode('utf-8')))
    return key


def _get_master_key() -> str:
    """获取加密主密钥：环境变量 > 自生成（不推荐）"""
    key = os.environ.get('API_ENCRYPTION_KEY', '')
    if key:
        return key
    
    # 回退：使用 SECRET_KEY 作为加密种子
    from flask import current_app
    try:
        return current_app.config.get('SECRET_KEY', 'fallback-key-not-secure')
    except RuntimeError:
        return os.environ.get('SECRET_KEY', 'fallback-key-not-secure')


def get_fernet() -> Fernet:
    """获取 Fernet 加密实例（单例）"""
    global _fernet_instance, _master_key
    
    current_key = _get_master_key()
    if _fernet_instance is not None and _master_key == current_key:
        return _fernet_instance
    
    _master_key = current_key
    derived_key = _derive_key(current_key)
    _fernet_instance = Fernet(derived_key)
    return _fernet_instance


def encrypt_api_key(plain_text: str) -> str:
    """加密 API Key
    Args:
        plain_text: 明文 API Key
    Returns:
        加密后的 base64 字符串，前缀 'enc:' 标识已加密
    """
    if not plain_text:
        return ''
    # 避免重复加密
    if plain_text.startswith('enc:'):
        return plain_text
    f = get_fernet()
    encrypted = f.encrypt(plain_text.encode('utf-8'))
    return 'enc:' + encrypted.decode('utf-8')


def decrypt_api_key(cipher_text: str) -> str:
    """解密 API Key
    Args:
        cipher_text: 加密后的字符串（以 'enc:' 开头）或明文
    Returns:
        明文 API Key
    """
    if not cipher_text:
        return ''
    # 如果不是加密格式，视为明文（向后兼容）
    if not cipher_text.startswith('enc:'):
        return cipher_text
    try:
        f = get_fernet()
        decrypted = f.decrypt(cipher_text[4:].encode('utf-8'))
        return decrypted.decode('utf-8')
    except Exception:
        # 解密失败，返回原始值（清理 'enc:' 前缀）
        return cipher_text[4:] if cipher_text.startswith('enc:') else cipher_text
