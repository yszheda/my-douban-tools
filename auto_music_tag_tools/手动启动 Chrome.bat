@echo off
chcp 65001 >nul
echo ============================================
echo   手动启动 Chrome 带调试端口
echo ============================================
echo.
echo 请按以下步骤操作：
echo.
echo 1. 关闭所有 Chrome 窗口
echo.
echo 2. 按 Win+R 打开"运行"对话框
echo.
echo 3. 复制并粘贴以下命令：
echo.
echo    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%TEMP%\chrome-douban
echo.
echo 4. 按回车启动 Chrome
echo.
echo 5. 在打开的浏览器中访问 https://music.douban.com 并登录
echo.
echo 6. 登录后，运行以下命令开始处理：
echo.
echo    python scripts/douban_chrome_simple.py --limit 5
echo.
echo ============================================
pause
