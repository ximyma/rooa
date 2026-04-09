@echo off
chcp 65001 >nul
echo ==========================================
echo TesseractOCR 安装脚本
echo ==========================================
echo.

REM 检查是否已安装
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo [✓] TesseractOCR 已安装在: C:\Program Files\Tesseract-OCR\
    goto :install_chi_sim
)

if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
    echo [✓] TesseractOCR 已安装在: C:\Program Files (x86)\Tesseract-OCR\
    goto :install_chi_sim
)

if exist "D:\Tesseract-OCR\tesseract.exe" (
    echo [✓] TesseractOCR 已安装在: D:\Tesseract-OCR\
    goto :install_chi_sim
)

if exist "E:\Tesseract-OCR\tesseract.exe" (
    echo [✓] TesseractOCR 已安装在: E:\Tesseract-OCR\
    goto :install_chi_sim
)

echo [!] 未检测到 TesseractOCR 安装
echo.
echo 请手动下载安装：
echo 1. 访问: https://github.com/UB-Mannheim/tesseract/releases
echo 2. 下载: tesseract-ocr-w64-setup-5.3.x.exe
echo 3. 运行安装程序，记住安装路径
echo 4. 安装完成后，下载中文字库 chi_sim.traineddata
echo.
pause
exit /b 1

:install_chi_sim
echo.
echo ==========================================
echo 检查中文字库
echo ==========================================

REM 查找 tessdata 目录
set "TESSDATA="

if exist "C:\Program Files\Tesseract-OCR\tessdata" (
    set "TESSDATA=C:\Program Files\Tesseract-OCR\tessdata"
)
if exist "C:\Program Files (x86)\Tesseract-OCR\tessdata" (
    set "TESSDATA=C:\Program Files (x86)\Tesseract-OCR\tessdata"
)
if exist "D:\Tesseract-OCR\tessdata" (
    set "TESSDATA=D:\Tesseract-OCR\tessdata"
)
if exist "E:\Tesseract-OCR\tessdata" (
    set "TESSDATA=E:\Tesseract-OCR\tessdata"
)

if "%TESSDATA%"=="" (
    echo [!] 未找到 tessdata 目录
    pause
    exit /b 1
)

echo [✓] 找到 tessdata 目录: %TESSDATA%

REM 检查中文字库
if exist "%TESSDATA%\chi_sim.traineddata" (
    echo [✓] 中文字库已安装
) else (
    echo [!] 未找到中文字库 chi_sim.traineddata
    echo.
    echo 请手动下载：
    echo https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata
    echo.
    echo 下载后放到: %TESSDATA%\
    echo.
    start https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata
)

echo.
echo ==========================================
echo 配置完成！
echo ==========================================
pause
