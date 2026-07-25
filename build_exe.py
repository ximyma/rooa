#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""智能服务办公平台 - PyInstaller 打包脚本"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import time

# 设置项目根目录
ROOT_DIR = Path(__file__).parent
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"

def clean_previous_builds():
    """清理之前的构建文件"""
    print("=== 清理之前的构建文件 ===")
    
    # 先尝试删除，失败时重试
    retry_count = 3
    for attempt in range(retry_count):
        try:
            for dir_name in ["build", "dist"]:
                dir_path = ROOT_DIR / dir_name
                if dir_path.exists():
                    print(f"  - 删除 {dir_name} (尝试 {attempt + 1})")
                    shutil.rmtree(dir_path, ignore_errors=True)
            
            for spec_file in ROOT_DIR.glob("*.spec"):
                print(f"  - 删除 {spec_file.name}")
                try:
                    spec_file.unlink()
                except Exception:
                    pass
            
            # 移除 startup.py（如果存在）
            startup_file = ROOT_DIR / "startup.py"
            if startup_file.exists():
                print("  - 删除 startup.py")
                try:
                    startup_file.unlink()
                except Exception:
                    pass
            
            break  # 成功则退出重试
        except Exception as e:
            if attempt < retry_count - 1:
                print(f"  [警告] 清理失败，等待后重试... ({e})")
                time.sleep(2)
            else:
                print(f"  [警告] 清理遇到问题，继续打包... ({e})")
    
    print("  OK: 清理完成")
    print()

def create_startup_script():
    """创建简化的启动脚本（用于打包）"""
    print("=== 创建启动脚本 ===")
    
    startup_content = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""智能服务办公平台 - 启动器"""

import sys
import os
from pathlib import Path

# 添加正确的路径
if getattr(sys, 'frozen', False):
    # 打包后的运行环境
    APP_PATH = Path(sys.executable).parent
else:
    # 开发环境
    APP_PATH = Path(__file__).parent

sys.path.insert(0, str(APP_PATH))

print("="*64)
print("  智能服务办公平台")
print("="*64)
print()
print("正在检查数据库状态...")

# 导入应用
os.chdir(str(APP_PATH))
from app import app, initialize_db
import webbrowser

# 检查数据库是否存在
db_path = APP_PATH / "oa.db"
if not db_path.exists():
    print("数据库不存在，正在初始化...")
    initialize_db()
else:
    print("数据库已存在，跳过初始化")

print()
print("正在启动服务...")
print("服务地址: http://127.0.0.1:5000")
print("按 CTRL+C 可停止服务")
print()

try:
    # 启动后自动打开浏览器
    webbrowser.open("http://127.0.0.1:5000")
except:
    pass

# 启动Flask应用
try:
    from waitress import serve
    print("使用 Waitress WSGI 服务器启动...")
    serve(app, host="127.0.0.1", port=5000)
except ImportError:
    print("使用 Flask 开发服务器启动...")
    app.run(host="127.0.0.1", port=5000, debug=False)
'''
    
    startup_path = ROOT_DIR / "startup.py"
    with open(startup_path, "w", encoding="utf-8") as f:
        f.write(startup_content)
    
    print("  OK: startup.py 创建完成")
    print()

def copy_necessary_files():
    """复制必要的资源文件到打包目录（临时）"""
    print("=== 准备打包资源 ===")
    
    # 确保必要的目录存在
    resources_needed = ["templates", "static", "config"]
    for dir_name in resources_needed:
        dir_path = ROOT_DIR / dir_name
        if dir_path.exists():
            print(f"  - 使用目录: {dir_name}")
        else:
            print(f"  - 注意: {dir_name} 目录不存在")
    
    print("  OK: 资源准备完成")
    print()

def build_with_pyinstaller():
    """使用 PyInstaller 打包"""
    print("=== 使用 PyInstaller 打包 ===")
    
    # PyInstaller spec 文件内容
    root_dir_str = str(ROOT_DIR).replace('\\', '\\\\')
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

# Project root directory
ROOT_DIR = Path(r'%s')

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
        'flask_caching',
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
        'smart_knowledge',
        'forms',
        
        # Document processing - COMPLETE SET
        'docx',
        'docx.document',
        'docx.oxml',
        'docx.oxml.ns',
        'docx.text',
        'docx.text.paragraph',
        'docx.text.run',
        'docx.table',
        'PyPDF2',
        'PyPDF2._reader',
        'PyPDF2._writer',
        'openpyxl',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        'openpyxl.cell',
        'openpyxl.reader',
        'openpyxl.reader.excel',
        'openpyxl.writer',
        'openpyxl.writer.excel',
        'openpyxl.xml',
        'openpyxl.xml.functions',
        'openpyxl.xml.constants',
        'openpyxl.styles',
        'openpyxl.utils',
        'et_xmlfile',
        'pypdf',
        'fitz',
        'PyMuPDF',
        'img2pdf',
        
        # Image processing
        'PIL',
        'PIL._imaging',
        'PIL.Image',
        'PIL.ImageFile',
        'PIL.ImageOps',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PIL.ImageFilter',
        'PIL.ImageChops',
        'PIL._tkinter_finder',
        'cv2',
        'cv2.cv2',
        'cv2.data',
        'numpy.core._multiarray_umath',
        'pytesseract',
        
        # Chinese NLP
        'jieba',
        'jieba.analyse',
        'jieba._compat',
        'jieba.posseg',
        
        # Data - COMPLETE SET
        'numpy',
        'numpy.core',
        'numpy.core.multiarray',
        'numpy.core._multiarray_umath',
        'numpy.core.numerictypes',
        'numpy.core.defchararray',
        'numpy.lib',
        'numpy.lib.format',
        'numpy.fft',
        'numpy.linalg',
        'numpy.random',
        'pandas',
        'pandas._libs',
        'pandas._libs.tslibs',
        'pandas.core',
        'pandas.core.frame',
        'pandas.core.series',
        'pandas.core.indexes',
        'pandas.io',
        'pandas.io.excel',
        'pandas.io.formats',
        
        # Network
        'requests',
        'requests.adapters',
        'requests.packages.urllib3',
        'requests.packages.urllib3.util',
        'bs4',
        'bs4.builder',
        'bs4.builder._lxml',
        'beautifulsoup4',
        'lxml',
        'lxml.etree',
        'lxml.html',
        
        # ML/NLP (optional)
        'sentence_transformers',
        'transformers',
        'transformers.modeling_utils',
        'transformers.tokenization_utils',
        'tokenizers',
        'huggingface_hub',
        'torch',
        'torch.nn',
        'torch.nn.functional',
        
        # Excel support - critical!
        'openpyxl.cell.cell',
        'openpyxl.styles.colors',
        'openpyxl.styles.fonts',
        'openpyxl.styles.fills',
        'openpyxl.styles.alignment',
        'openpyxl.styles.borders',
        'openpyxl.styles.protection',
        'openpyxl.styles.colors',
        'openpyxl.styles.numbers',
        'openpyxl.workbook.child',
        'openpyxl.worksheet.worksheet',
        'openpyxl.worksheet.dimensions',
        'openpyxl.worksheet.page',
        'openpyxl.utils.cell',
        'openpyxl.utils.exceptions',
        'openpyxl.xml.functions',
        
        # Misc
        'pickle',
        'json',
        're',
        'datetime',
        'collections',
        'time',
        'os',
        'sys',
        'pathlib',
        'threading',
        'logging',
        'tempfile',
        'shutil',
        'zipfile',
        'struct',
        'array',
        'math',
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
'''
    
    spec_path = ROOT_DIR / "OA_System.spec"
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec_content % root_dir_str)
    
    print("  - 已创建 PyInstaller spec 文件")
    print()
    print("现在运行 PyInstaller 进行打包...")
    print("(这个过程可能需要几分钟时间，请耐心等待...)")
    print()
    
    # 运行 PyInstaller
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_path)
    ]
    
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    
    return result.returncode == 0

def prepare_dist_package():
    """准备最终的分发包"""
    print("\n=== 准备分发包 ===")
    
    dist_path = DIST_DIR
    if not dist_path.exists():
        print("  ERROR: dist 目录不存在")
        return False
    
    # 创建必要的空目录
    empty_dirs = ["uploads", "uploads/proofread", "uploads/suggestion",
                  "uploads/audio", "uploads/pdf", "uploads/chat",
                  "uploads/knowledge", "uploads/shared", "uploads/archive"]

    for dir_name in empty_dirs:
        dir_path = dist_path / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  - 创建目录: {dir_name}")

    # 复制 templates 目录
    templates_src = ROOT_DIR / "templates"
    templates_dst = dist_path / "templates"
    if templates_src.exists():
        import shutil
        if templates_dst.exists():
            shutil.rmtree(templates_dst)
        shutil.copytree(templates_src, templates_dst)
        print(f"  - 复制目录: templates")
    else:
        print(f"  - 警告: templates 目录不存在")

    # 复制 static 目录
    static_src = ROOT_DIR / "static"
    static_dst = dist_path / "static"
    if static_src.exists():
        import shutil
        if static_dst.exists():
            shutil.rmtree(static_dst)
        shutil.copytree(static_src, static_dst)
        print(f"  - 复制目录: static")
    else:
        print(f"  - 警告: static 目录不存在")

    # （注意：Python源代码已通过 PyInstaller 打包进 exe，不暴露源文件）
    
    # 创建 README 文件
    readme_content = '''智能服务办公平台
===================

快速开始
--------

1. 首次运行：
   - 双击 "智能服务办公平台.exe"
   - 程序会自动初始化数据库
   - 浏览器会自动打开

2. 登录信息：
   - 用户名：admin
   - 密码：admin123
   - 重要：首次登录后请立即修改密码！

目录说明
--------

- 智能服务办公平台.exe：主程序文件
- templates/：HTML模板
- static/：静态资源（CSS/JS/图片等）
- config/：配置文件
- uploads/：上传文件目录
- oa.db：数据库文件（自动生成）

故障排除
--------

- 如果无法启动，检查端口5000是否被占用
- 如果数据丢失，删除 oa.db 重新初始化
- 查看控制台信息了解详细错误

技术支持
--------

如有问题请联系技术支持团队。
'''
    
    readme_path = dist_path / "README.txt"
    with open(readme_path, "w", encoding="utf-8-sig") as f:
        f.write(readme_content)
    
    print(f"  - 创建说明文件: README.txt")
    
    # 创建数据备份脚本
    backup_script = '''@echo off
chcp 65001 >nul
echo 正在备份数据库...
for /f "delims=" %%a in ('wmic OS Get localdatetime ^| find "."') do set dt=%%a
set yyyy=%dt:~0,4%
set mm=%dt:~4,2%
set dd=%dt:~6,2%
set hh=%dt:~8,2%
set min=%dt:~10,2%
set sec=%dt:~12,2%

if exist oa.db (
    copy oa.db "oa.db.backup_%yyyy%%mm%%dd%_%hh%%min%%sec%.db"
    echo 备份完成！
) else (
    echo 数据库文件 oa.db 不存在！
)
pause
'''
    
    backup_path = dist_path / "备份数据库.bat"
    with open(backup_path, "w", encoding="gbk") as f:
        f.write(backup_script)
    
    print(f"  - 创建备份脚本: 备份数据库.bat")
    
    # 创建配置文件
    config_dir = dist_path / "config"
    config_dir.mkdir(exist_ok=True)
    
    system_config = '''{
    "knowledge_base": {
        "embedding_model_path": "models/all-MiniLM-L6-v2",
        "use_local_model": true,
        "max_file_size_mb": 100,
        "batch_size": 10,
        "auto_extract_keywords": true,
        "auto_generate_summary": true,
        "auto_tag": true
    },
    "ocr": {
        "enabled": false,
        "tesseract_cmd": "C:\\\\Program Files\\\\Tesseract-OCR\\\\tesseract.exe",
        "tessdata_dir": "C:\\\\Program Files\\\\Tesseract-OCR\\\\tessdata",
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
        "auto_run": true,
        "check_interval_hours": 24,
        "notify_on_overdue": true
    },
    "document": {
        "max_extracted_length": -1,
        "max_preview_length": 100000,
        "max_ai_sample_length": 5000,
        "max_upload_size_mb": 100
    }
}'''
    
    with open(config_dir / "system_config.json", "w", encoding="utf-8") as f:
        f.write(system_config)
    
    print(f"  - 创建配置文件: config/system_config.json")
    
    print()
    print("OK: 分发包准备完成！")
    
    # 计算大小
    dist_size_mb = sum(f.stat().st_size for f in dist_path.rglob('*') if f.is_file()) / (1024*1024)
    print(f"分发包大小: {dist_size_mb:.2f} MB")
    
    return True

def show_build_summary():
    """显示构建总结"""
    print("\n" + "="*64)
    print("  构建完成！")
    print("="*64)
    print()
    print(f"输出目录: {DIST_DIR.absolute()}")
    print()
    print("下一步：")
    print("1. 测试打包后的程序")
    print("2. 压缩 dist 目录")
    print("3. 分发给客户")
    print()
    print("重要提示：")
    print("- 首次运行会自动初始化数据库")
    print("- 默认登录：admin / admin123")
    print("- 请确保防火墙允许5000端口")
    print()

def main():
    print("\n" + "="*64)
    print("  智能服务办公平台 - 打包构建")
    print("="*64)
    print()
    
    # 检查必要条件
    try:
        import PyInstaller
    except ImportError:
        print("ERROR: PyInstaller 未安装！")
        print("请运行: pip install pyinstaller")
        return False
    
    # 检查 waitress
    try:
        import waitress
    except ImportError:
        print("INFO: 安装生产服务器 Waitress...")
        subprocess.run([sys.executable, "-m", "pip", "install", "waitress"])
    
    try:
        # 1. 清理
        clean_previous_builds()
        
        # 2. 创建启动脚本
        create_startup_script()
        
        # 3. 准备资源
        copy_necessary_files()
        
        # 4. 打包
        if not build_with_pyinstaller():
            print("\nERROR: 打包失败！")
            return False
        
        # 5. 准备分发包
        if not prepare_dist_package():
            print("\nERROR: 分发包准备失败！")
            return False
        
        # 6. 总结
        show_build_summary()
        
        return True
        
    except Exception as e:
        print(f"\nERROR: 构建过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
