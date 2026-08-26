@echo off
title 27秋招日报 - 数据更新
echo ============================================
echo   27秋招日报 · 数据抓取更新
echo ============================================
echo.
cd /d "%~dp0"

set PY=C:\Users\24345\.skillhub\runtime\python.exe
if not exist "%PY%" set PY=python

echo [1/2] 正在从腾讯文档抓取最新秋招数据...
"%PY%" "%~dp0fetch_data.py"
if errorlevel 1 (
    echo.
    echo [失败] 数据抓取失败，请检查网络连接后重试。
    echo.
    pause
    exit /b 1
)

echo [2/2] 数据更新完成！
echo.
echo 数据文件：data.js
echo 打开 index.html 即可查看最新秋招日报
echo.
pause
