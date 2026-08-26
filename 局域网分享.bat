@echo off
title 27秋招日报 - 局域网分享
echo ============================================
echo   27秋招日报 · 局域网分享服务
echo ============================================
echo.
echo 启动后，同一 WiFi/局域网内的人可用浏览器访问：
echo   你的电脑上自动打开预览窗口
echo   其他人访问: http://本机IP:8000
echo.
echo 通过本服务打开网页，DeepSeek/邮件 刷新按钮可用。
echo 关闭本窗口即停止分享。
echo.

cd /d "%~dp0"
set PY=C:\Users\24345\.skillhub\runtime\python.exe
if not exist "%PY%" set PY=python

REM 获取本机局域网 IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do set IP=%%a
set IP=%IP: =%
if "%IP%"=="" set IP=127.0.0.1

echo 访问地址: http://%IP%:8000
echo.
REM 延迟打开浏览器预览
start "" http://127.0.0.1:8000

"%PY%" "%~dp0server.py" 8000
pause
