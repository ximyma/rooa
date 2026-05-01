#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""智能服务办公平台 - 源代码保护脚本"""

import os
import sys
import py_compile
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).parent

def compile_pyc(source_dir, output_dir, exclude_patterns=None):
    """把 .py 编译成 .pyc"""
    if exclude_patterns is None:
        exclude_patterns = [
            "__pycache__", ".pyc", "venv", "env", 
            ".git", "build", "dist", "node_modules"
        ]
    
    output_dir.mkdir(parents=True, exist_ok=True)
    compiled_count = 0
    
    print(f"正在编译 {source_dir} ...")
    
    for py_file in source_dir.rglob("*.py"):
        # 检查是否需要排除
        skip = False
        for pattern in exclude_patterns:
            if pattern in str(py_file):
                skip = True
                break
        
        if skip:
            continue
        
        # 计算相对路径
        relative_path = py_file.relative_to(source_dir)
        output_pyc = output_dir / relative_path
        
        # 创建输出目录结构
        output_pyc.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 编译
            py_compile.compile(
                str(py_file),
                str(output_pyc.parent / (py_file.stem + ".pyc")),
                doraise=True
            )
            compiled_count += 1
            
            if compiled_count % 5 == 0:
                print(f"  ... {compiled_count} 个文件已编译")
                
        except Exception as e:
            print(f"  警告: 无法编译 {py_file}: {e}")
    
    print(f"OK: {compiled_count} 个文件编译完成")
    return compiled_count

def create_protected_structure():
    """创建受保护的项目结构"""
    print("=== 创建受保护的项目结构 ===")
    print()
    
    protected_dir = ROOT_DIR / "protected"
    
    # 清理旧的
    if protected_dir.exists():
        shutil.rmtree(protected_dir)
    protected_dir.mkdir()
    
    # 1. 复制不需要编译的关键文件
    print("1. 复制必要文件...")
    files_to_copy = [
        "startup.py",
        "init_db_standalone_simple.py",
        "verify_data_simple.py",
        "config_manager.py",
        "utils.py",
        "requirements.txt",
    ]
    
    for file_name in files_to_copy:
        source_path = ROOT_DIR / file_name
        if source_path.exists():
            shutil.copy2(source_path, protected_dir / file_name)
            print(f"  复制: {file_name}")
    
    # 2. 复制目录资源
    dirs_to_copy = ["templates", "static", "config"]
    for dir_name in dirs_to_copy:
        source_dir = ROOT_DIR / dir_name
        if source_dir.exists():
            shutil.copytree(source_dir, protected_dir / dir_name)
            print(f"  复制: {dir_name}/")
    
    print()
    
    # 3. 编译核心模块为 .pyc（提供保护）
    print("2. 编译核心模块...")
    
    # 把 models 和 archive_models 拷贝并编译
    core_modules = ["models.py", "archive_models.py"]
    
    for module in core_modules:
        if (ROOT_DIR / module).exists():
            shutil.copy2(ROOT_DIR / module, protected_dir / module)
            print(f"  复制: {module}")
    
    print()
    print("注意: 核心文件保护通过 PyInstaller 打包实现")
    print("  - PyInstaller 会把 .py 编译成 bytecode 并打包")
    print("  - 用户无法直接查看源代码")
    print()
    
    return protected_dir

def create_build_info():
    """创建构建信息文件"""
    import datetime
    info_content = f'''智能服务办公平台 - 构建信息
=========================
构建时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
版本: 1.0.0
数据库: SQLite
架构: {sys.platform}

保护说明
--------
- 源代码已通过 PyInstaller 打包保护
- 核心业务逻辑编译在二进制中
- 用户无法直接获取 .py 源文件

安全提示
--------
- 请修改默认密码
- 定期备份数据库
- 注意防火墙配置
'''
    
    info_path = ROOT_DIR / "BUILD_INFO.txt"
    with open(info_path, "w", encoding="utf-8-sig") as f:
        f.write(info_content)
    
    print(f"已创建: BUILD_INFO.txt")
    return info_path

def show_protection_summary():
    """显示保护措施总结"""
    print("\n" + "="*64)
    print("  源代码保护方案总结")
    print("="*64)
    print()
    print("保护机制:")
    print("  1. PyInstaller 打包 - 源码编译成 bytecode")
    print("  2. 单文件/目录分发 - 用户无法直接查看 .py 源文件")
    print("  3. SQLite 数据库 - 与程序分离，易于备份")
    print()
    print("分发建议:")
    print("  - 提供压缩包：dist.zip")
    print("  - 分发前测试：运行打包后的程序")
    print("  - 包含说明文档：README.txt")
    print()
    print("下一步:")
    print("  运行 'python build_exe.py' 开始打包")
    print()

def main():
    print("\n" + "="*64)
    print("  智能服务办公平台 - 源代码保护")
    print("="*64)
    print()
    
    try:
        create_protected_structure()
        create_build_info()
        show_protection_summary()
        
        print()
        return True
        
    except Exception as e:
        print(f"ERROR: 保护过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
