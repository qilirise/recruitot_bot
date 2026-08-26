@echo off
title 27秋招 - GitHub 推送配置
echo ============================================
echo   27秋招日报 · 推送 GitHub 配置
echo ============================================
echo.
echo 本脚本将:
echo   1. 配置 git 代理 (github.com 走 127.0.0.1:7897)
echo   2. 配置远程仓库 recruitot_bot
echo   3. 保存 GitHub 凭据（需要你粘贴 token）
echo   4. 推送代码
echo.
echo 请准备好你的 GitHub token (github_pat_...)
echo.
set /p TOKEN=请输入 GitHub token 并回车: 
echo.
if "%TOKEN%"=="" (
  echo 未输入 token，退出
  pause
  exit /b 1
)

set PATH=C:\Program Files\Git\bin;%PATH%
cd /d "%~dp0"

echo.
echo [1/4] 配置 git 代理...
git config --global http.https://github.com.proxy http://127.0.0.1:7897

echo [2/4] 配置远程仓库...
git remote remove origin 2>nul
git remote add origin https://github.com/qilirise/recruitot_bot.git

echo [3/4] 保存凭据...
echo protocol=https>%TEMP%\ghcred.txt
echo host=github.com>>%TEMP%\ghcred.txt
echo username=qilirise>>%TEMP%\ghcred.txt
echo password=%TOKEN%>>%TEMP%\ghcred.txt
type %TEMP%\ghcred.txt | git credential approve
del %TEMP%\ghcred.txt

echo [4/4] 推送代码...
git push -u origin main

echo.
if %errorlevel%==0 (
  echo ============================================
  echo   推送成功! 仓库: https://github.com/qilirise/recruitot_bot
  echo ============================================
) else (
  echo 推送失败，请检查 token 权限（Contents 需为 Read and write）
)
pause
