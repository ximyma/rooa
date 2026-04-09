@echo off
REM OOA智能服务办公平台 - 启动脚本

echo =====================================================
echo OOA智能服务办公平台
echo =====================================================
echo.

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境未找到，请先运行 setup_env.bat 创建虚拟环境
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 运行初始化脚本（首次运行）
if not exist ".env" (
    echo [信息] 首次运行，正在初始化项目...
    python init_project.py
    echo.
)

REM 启动应用
echo [信息] 启动应用...
echo.
python app.py

pause
