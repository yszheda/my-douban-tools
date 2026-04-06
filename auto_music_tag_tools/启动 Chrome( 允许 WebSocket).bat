@echo off
chcp 65001 >nul
echo ============================================
echo   启动 Chrome 带调试端口（允许 WebSocket）
echo ============================================
echo.
echo 正在启动 Chrome...
echo.

REM 关闭现有 Chrome 进程
taskkill /IM chrome.exe /F >nul 2>&1

timeout /t 2 /nobreak >nul

REM 启动 Chrome 带调试端口
start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=%TEMP%\chrome-douban-profile https://music.douban.com

echo.
echo Chrome 已启动！
echo.
echo 请在打开的浏览器中登录豆瓣音乐
echo.
echo 登录后按回车继续...
pause

echo.
echo 正在连接 Chrome...
python scripts/douban_chrome_simple.py --port 9222 --limit 5

pause
