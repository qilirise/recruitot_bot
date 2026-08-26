@echo off
title 27秋招日报 - 取消每日自动更新
echo 正在删除计划任务 Qiuzhao27DailyUpdate ...
schtasks /Delete /F /TN "Qiuzhao27DailyUpdate"
if errorlevel 1 (
    echo [失败] 删除失败，或任务不存在。
) else (
    echo [成功] 已取消每日自动更新。
)
pause
