# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

# Project root directory
ROOT_DIR = Path(r'D:\\myapps\\rooa')

block_cipher = None

a = Analysis(
    ['startup.py'],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('config', 'config'),
    ],
    hiddenimports=[
        'flask',
        'flask_sqlalchemy',
        'flask_login',
        'flask_wtf',
        'werkzeug',
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'waitress',
        'models',
        'archive_models',
        'config_manager',
        'utils',
        'config',
        'app',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='智能服务办公平台',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可设置为 ico 文件路径
)
