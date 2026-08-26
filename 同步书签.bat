@echo off
title 27秋招日报 - 同步书签
echo ============================================
echo   27秋招日报 · 同步 Edge 书签为已投递
echo ============================================
echo.
echo 将读取 Edge「找工作!/官网」收藏夹，
echo 自动把匹配到的公司标记为「已投递」。
echo.

cd /d "%~dp0"
set PY=C:\Users\24345\.skillhub\runtime\python.exe
if not exist "%PY%" set PY=python

echo [1/1] 正在同步书签...
"%PY%" "%~dp0sync_bookmarks.py"
if errorlevel 1 (
    echo.
    echo [失败] 同步失败，请检查后重试。
    echo.
    pause
    exit /b 1
)

echo.
echo 同步完成！刷新 index.html 或 tracked.html 即可查看。
echo.
pause
