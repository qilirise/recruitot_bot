@echo off
title 27秋招 - 配置GitHub自动同步
echo ============================================
echo   27秋招日报 · GitHub 自动同步配置
echo ============================================
echo.
echo 本脚本只需运行一次：
echo   1. 配置 git 代理（github.com 走 127.0.0.1:7897）
echo   2. 保存你的 GitHub token 到 Windows 凭据管理器
echo   3. 之后「更新数据.bat」会自动同步到 GitHub
echo.
echo 请粘贴你的 GitHub token（github_pat_... 开头）
echo.
set /p TOKEN=GitHub Token: 
echo.
if "%TOKEN%"=="" (
  echo 未输入 token，退出
  pause
  exit /b 1
)

set PATH=C:\Program Files\Git\bin;%PATH%
cd /d "%~dp0"

echo [1/3] 配置 git 代理...
git config --global http.https://github.com.proxy http://127.0.0.1:7897

echo [2/3] 保存凭据...
echo protocol=https>%TEMP%\gh_cred.txt
echo host=github.com>>%TEMP%\gh_cred.txt
echo username=qilirise>>%TEMP%\gh_cred.txt
echo password=%TOKEN%>>%TEMP%\gh_cred.txt
type %TEMP%\gh_cred.txt | git credential approve
del %TEMP%\gh_cred.txt

echo [3/3] 测试推送认证...
git ls-remote origin HEAD >nul 2>&1
if %errorlevel%==0 (
  echo.
  echo ============================================
  echo   配置成功! 自动同步已启用
  echo   以后每次运行「更新数据.bat」会自动上传到 GitHub
  echo ============================================
) else (
  echo.
  echo 认证失败，请检查 token 权限（Contents 需 Read and write）
)
pause
