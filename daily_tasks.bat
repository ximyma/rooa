@echo off
chcp 65001 >nul
cd /d C:\Users\Administrator\Desktop\ooa

echo ===== 开始执行每日简报生成任务 =====
echo 时间: %date% %time%
echo.

REM 1. 石城县政府网站全部栏目监测
echo [1/4] 执行石城县政府网站监测...
python run_monitor.py > logs\monitor_%date:~0,4%%date:~5,2%%date:~8,2%.log 2>&1
echo 监测完成

echo.
echo ===== 所有任务执行完成 =====
echo 时间: %date% %time%
