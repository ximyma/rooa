@echo off
REM 智能服务办公平台 - 环境设置脚本

echo =====================================================
echo 智能服务办公平台 - 环境设置
echo =====================================================
echo.

REM 检查 Python 是否已安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [信息] Python 环境检查通过
echo.

REM 创建虚拟环境
if not exist "venv" (
    echo [信息] 创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo [信息] 虚拟环境创建成功
) else (
    echo [信息] 虚拟环境已存在
)

REM 激活虚拟环境并安装依赖
echo [信息] 激活虚拟环境并安装依赖...
call venv\Scripts\activate.bat

echo [信息] 更新 pip...
python -m pip install --upgrade pip

echo [信息] 安装项目依赖...
pip install -r requirements.txt

if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo.
echo =====================================================
echo 环境设置完成！
echo =====================================================
echo.
echo 下一步：
echo   1. 运行 start.bat 启动应用
echo   2. 访问 http://127.0.0.1:5000
echo   3. 使用默认账号登录（用户名: admin，密码: admin123）
echo.
pause
