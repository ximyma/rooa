@echo off
chcp 65001 >nul
echo ============================================================
echo          智能服务办公平台 - 系统初始化
echo ============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python,请先安装Python 3.7+
    pause
    exit /b 1
)

echo [信息] Python已安装
echo.

REM 运行系统初始化脚本
echo [信息] 开始系统初始化...
echo.
python init_system.py

if errorlevel 1 (
    echo.
    echo [错误] 系统初始化失败,请检查错误信息
    pause
    exit /b 1
)

echo.
echo ============================================================
echo          系统初始化完成!
echo ============================================================
echo.
echo 下一步: 运行 "启动系统.bat" 启动服务
echo.
pause
