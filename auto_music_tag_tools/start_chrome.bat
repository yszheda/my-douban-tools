@echo off
chcp 65001 >nul
echo ============================================
echo   启动 Chrome (带远程调试端口)
echo ============================================
echo.

REM Chrome 路径
set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME_PATH%" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

if not exist "%CHROME_PATH%" (
    echo [错误] 未找到 Chrome，请检查安装路径
    pause
    exit /b 1
)

echo [1/2] 启动 Chrome...
start "" "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome-douban-profile" https://music.douban.com

echo.
echo [2/2] 请在打开的浏览器中登录豆瓣音乐
echo.
echo 登录后可运行:
echo   python scripts/douban_chrome_simple.py --limit 5
echo.
echo 按任意键关闭此窗口...
pause >nul
