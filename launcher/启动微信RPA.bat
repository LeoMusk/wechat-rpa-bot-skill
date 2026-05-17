@echo off
chcp 65001 >nul
title 微信 RPA 启动器
cd /d "%~dp0.."

echo ============================================
echo            微信 RPA 服务启动器
echo ============================================
echo.
echo [1/2] 清理可能残留的旧进程...
python scripts\stop_server.py
echo.
echo [2/2] 正在启动服务，请稍候（约 10-30 秒）...
set WEBOT_BACKEND_MODE=1
set HEADLESS_MODE=1
set DISABLE_WEBVIEW=1
set NO_BROWSER=1
python scripts\start_server.py
if errorlevel 1 goto failed

echo.
echo ============================================
echo   微信 RPA 服务已就绪。
echo.
echo   请回到与 AI 的对话窗口，它会自动检测并继续，
echo   您无需在对话里回复任何内容。
echo.
echo   此窗口可以最小化；关闭它不会影响后台服务。
echo ============================================
echo.
pause
exit /b 0

:failed
echo.
echo ============================================
echo   启动失败。请把本窗口顶部的报错信息截图发给 AI。
echo ============================================
echo.
pause
exit /b 1
