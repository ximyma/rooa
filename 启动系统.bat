@echo off
chcp 65001 >nul
title 智能服务办公平台

echo ============================================================
echo          智能服务办公平台 - 启动服务
echo ============================================================
echo.

REM 检查数据库是否存在
if not exist "oa.db" (
    echo [提示] 数据库不存在,建议先运行 "初始化系统.bat"
    echo.
    set /p confirm="是否继续启动? (y/n): "
    if /i not "%confirm%"=="y" (
        echo.
        echo [信息] 已取消启动
        pause
        exit /b 0
    )
    echo.
)

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python,请先安装Python 3.7+
    pause
    exit /b 1
)

echo [信息] 正在启动系统...
echo.
echo ============================================================
echo   系统启动中,请勿关闭此窗口!
echo   访问地址: http://127.0.0.1:5000
echo   按 Ctrl+C 停止服务
echo ============================================================
echo.

REM 启动Flask应用
python app.py

if errorlevel 1 (
    echo.
    echo [错误] 系统启动失败
    pause
)
