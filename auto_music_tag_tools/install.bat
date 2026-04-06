@echo off
chcp 65001 >nul
echo ============================================
echo   安装豆瓣音乐自动化脚本依赖
echo ============================================
echo.

echo [1/2] 安装 Playwright...
python -m pip install playwright

echo.
echo [2/2] 安装 Chromium 浏览器...
playwright install chromium

echo.
echo ============================================
echo   安装完成!
echo ============================================
echo.
echo 下一步:
echo 1. 获取豆瓣 Cookie (打开 scripts/get_douban_cookie.html)
echo 2. 将 Cookie 保存到 scripts/douban_cookie.txt
echo 3. 运行 scripts/run.bat 开始处理
echo.
pause
