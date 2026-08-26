@echo off
title 27秋招日报 - 设置每日自动更新
echo ============================================
echo   27秋招日报 · 每日自动更新设置
echo ============================================
echo.
echo 本脚本将注册一个 Windows 计划任务：
echo   - 任务名：Qiuzhao27DailyUpdate
echo   - 时间：每天 09:00 自动抓取最新秋招数据
echo.
set /p CONFIRM=确认设置每日 09:00 自动更新？(Y/N)：
if /i not "%CONFIRM%"=="Y" (
    echo 已取消。
    pause
    exit /b 0
)

cd /d "%~dp0"
set PY=C:\Users\24345\.skillhub\runtime\python.exe
if not exist "%PY%" set PY=python

echo.
echo [1/2] 测试数据抓取...
"%PY%" "%~dp0fetch_data.py"
if errorlevel 1 (
    echo [失败] 数据抓取测试失败，请检查网络后重试。
    pause
    exit /b 1
)

echo.
echo [2/2] 注册计划任务（每天 09:00）...
schtasks /Create /F /TN "Qiuzhao27DailyUpdate" ^
    /TR "\"%PY%\" \"%~dp0fetch_data.py\"" ^
    /SC DAILY /ST 09:00

if errorlevel 1 (
    echo [失败] 计划任务创建失败，可能需要管理员权限。
    echo 请右键「以管理员身份运行」本脚本。
    pause
    exit /b 1
)

echo.
echo ============================================
echo   已设置成功！每天 09:00 将自动更新数据
echo   取消方法：运行 取消每日自动更新.bat
echo ============================================
pause
