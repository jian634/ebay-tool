@echo off
chcp 65001 >nul
echo.
echo  eBay 汽配竞品分析工具 - 启动中...
echo  eBay Auto Parts Competitor Analysis Tool - Starting...
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [错误] 未检测到 Python，请先安装 Python 3.x
    echo  [Error] Python not found. Please install Python 3.x from python.org
    echo.
    pause
    exit /b 1
)

echo  正在启动本地服务器 (端口 8080)...
echo  Starting local server on port 8080...
echo.
echo  请在浏览器访问: http://localhost:8080
echo  Open in browser: http://localhost:8080
echo.
echo  按 Ctrl+C 停止服务器 / Press Ctrl+C to stop
echo.

REM 等待1秒后自动打开浏览器
timeout /t 1 /nobreak >nul
start http://localhost:8080

REM 启动 Python HTTP 服务器
cd /d "%~dp0"
python -m http.server 8080
