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

echo [2/3] 数据更新完成！
echo.

echo [3/3] 同步到 GitHub...
set PATH=C:\Program Files\Git\bin;%PATH%
git add -A
git commit -m "每日数据更新 %date% %time%" >nul 2>&1
git push origin main
if errorlevel 1 (
    echo.
    echo [警告] GitHub 同步失败（可能未配置 token 或网络问题）
    echo 数据已保存在本地，可稍后双击「配置GitHub同步.bat」配置后手动同步
) else (
    echo GitHub 同步成功!
)

echo.
echo 数据文件：data.js
echo 打开 index.html 即可查看最新秋招日报
echo.
pause
