@echo off
title 27秋招 - 读取邮件
echo ============================================
echo   27秋招日报 · 读取 Outlook 邮件
echo ============================================
echo.
cd /d "%~dp0"
set PY=C:\Users\24345\.skillhub\runtime\python.exe
if not exist "%PY%" set PY=python

"%PY%" "%~dp0read_mail.py"
if errorlevel 1 (
    echo.
    echo [失败] 读取失败，请检查 mail_config.json 配置。
    echo.
    pause
    exit /b 1
)

echo.
echo 完成！打开 mail.html 查看识别结果。
echo.
pause
