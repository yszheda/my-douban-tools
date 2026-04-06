@echo off
chcp 65001 >nul
echo ============================================
echo   豆瓣音乐批量处理工具 - 快速启动
echo ============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.7+
    pause
    exit /b 1
)

echo [1/4] 检查 Python 环境... OK
echo.

REM 检查 playwright
python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo [2/4] 安装 Playwright...
    pip install playwright
    playwright install chromium
) else (
    echo [2/4] Playwright 已安装
)
echo.

REM 检查 Cookie
if not exist "%~dp0douban_cookie.txt" (
    echo [3/4] Cookie 文件不存在
    echo.
    echo 请先获取豆瓣 Cookie:
    echo 1. 在浏览器中打开：%~dp0get_douban_cookie.html
    echo 2. 登录豆瓣账号
    echo 3. 点击"获取 Cookie"按钮
    echo 4. 复制并保存到：%~dp0douban_cookie.txt
    echo.
    pause

    REM 打开 Cookie 获取页面
    start "%~dp0get_douban_cookie.html"

    echo.
    echo 按任意键继续检查...
    pause >nul
) else (
    echo [3/4] Cookie 文件已存在
)
echo.

echo [4/4] 选择运行模式
echo.
echo   1. 测试模式 (处理前 5 个专辑)
echo   2. 完整模式 (处理所有专辑)
echo   3. 空运行 (只扫描，不执行)
echo   4. 退出
echo.
set /p choice="请选择 (1-4): "

if "%choice%"=="1" (
    echo.
    echo 启动测试模式...
    python "%~dp0run_douban_automation.py" --test
) else if "%choice%"=="2" (
    echo.
    echo 启动完整模式...
    python "%~dp0run_douban_automation.py" --all
) else if "%choice%"=="3" (
    echo.
    echo 启动空运行模式...
    python "%~dp0run_douban_automation.py" --dry-run
) else if "%choice%"=="4" (
    exit /b 0
) else (
    echo 无效选择
)

echo.
pause
