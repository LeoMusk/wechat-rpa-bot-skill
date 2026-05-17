@echo off
chcp 65001 >nul
title 微信 RPA 停止器
cd /d "%~dp0.."

echo ============================================
echo            微信 RPA 服务停止器
echo ============================================
echo.
echo 正在停止微信 RPA 服务...
python scripts\stop_server.py
echo.
echo   微信 RPA 服务已停止。
echo ============================================
echo.
pause
