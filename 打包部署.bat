@echo off
chcp 65001 >nul
echo ============================================================
echo   Smart Office System - Build Package Tool
echo ============================================================
echo.

set VENV_DIR=venv_build
set REQUIREMENTS=requirements.txt
set APP_DIR=%~dp0
cd /d "%APP_DIR%"

set MIRROR_URL=https://mirrors.aliyun.com/pypi/simple/

echo [INFO] Working directory: %CD%
echo [INFO] Using mirror: %MIRROR_URL%
echo.

:: Check Python
echo ============================================================
echo   Step 1: Check Python Environment
echo ============================================================
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.7+
    echo Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VER=%%i
echo [OK] Python: %PYTHON_VER%
echo.

:: Clean old virtual environment
echo ============================================================
echo   Step 2: Prepare Virtual Environment
echo ============================================================
if exist "%VENV_DIR%\" (
    echo [INFO] Removing old virtual environment...
    rmdir /s /q "%VENV_DIR%" 2>nul
    timeout /t 2 >nul
)
echo [INFO] Creating virtual environment: %VENV_DIR%
python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment!
    pause
    exit /b 1
)
echo [OK] Virtual environment created
echo.

:: Activate virtual environment
echo ============================================================
echo   Step 3: Activate Virtual Environment
echo ============================================================
call "%VENV_DIR%\Scripts\activate.bat"
echo [OK] Virtual environment activated
echo.

:: Configure pip mirror
echo ============================================================
echo   Step 4: Configure pip mirror
echo ============================================================
set PIP_INDEX_URL=%MIRROR_URL%
set PIP_TRUSTED_HOST=mirrors.aliyun.com
echo [OK] Mirror configured: %MIRROR_URL%
echo.

:: Upgrade pip
echo ============================================================
echo   Step 5: Upgrade pip
echo ============================================================
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
echo.

:: Check requirements.txt
if not exist "%REQUIREMENTS%" (
    echo [ERROR] %REQUIREMENTS% not found!
    pause
    exit /b 1
)

:: Install dependencies
echo ============================================================
echo   Step 6: Install Dependencies
echo ============================================================
echo [INFO] Installing from %REQUIREMENTS% using mirror...
echo.
"%VENV_DIR%\Scripts\pip.exe" install -r "%REQUIREMENTS%" -i %MIRROR_URL%
if errorlevel 1 (
    echo [WARNING] Some packages may have failed. Continuing...
)
echo.
echo [OK] Dependencies installed
echo.

:: Check project files
echo ============================================================
echo   Step 7: Check Project Files
echo ============================================================
set FILE_CHECK=1

if not exist "app.py" (
    echo [ERROR] app.py not found!
    set FILE_CHECK=0
)
if not exist "init_db_standalone_simple.py" (
    echo [ERROR] init_db_standalone_simple.py not found!
    set FILE_CHECK=0
)
if not exist "models.py" (
    echo [ERROR] models.py not found!
    set FILE_CHECK=0
)
if not exist "templates\" (
    echo [ERROR] templates not found!
    set FILE_CHECK=0
)
if not exist "static\" (
    echo [ERROR] static not found!
    set FILE_CHECK=0
)

if %FILE_CHECK%==0 (
    echo.
    echo [ERROR] File check failed!
    pause
    exit /b 1
)

echo [OK] All files checked
echo.

:: Build with PyInstaller
echo ============================================================
echo   Step 8: Build with PyInstaller
echo ============================================================
echo.
echo [INFO] Running build script...
echo.
"%VENV_DIR%\Scripts\python.exe" build_exe.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo   [ERROR] Build failed!
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Build completed!
echo ============================================================
echo.
echo Output: %CD%\dist
echo.
echo ============================================================
echo   Next steps:
echo ============================================================
echo.
echo 1. Test the package:
echo    Go to dist folder, run: 智能服务办公平台.exe
echo.
echo 2. Verify database initialization:
echo    Should automatically create oa.db
echo.
echo 3. Test login:
echo    Username: admin
echo    Password: admin123
echo.
echo ============================================================
echo.

set /p OPEN_DIST="Open dist folder? (Y/N): "
if /i "%OPEN_DIST%"=="Y" (
    if exist "dist\" (
        explorer dist
    )
)

echo.
echo Done!
pause
