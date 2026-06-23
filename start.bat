@echo off
chcp 65001 >nul
echo.
echo  eBay 汽配竞品分析工具 - 启动中...
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [错误] 未检测到 Python，请先安装 Python 3.x
    pause
    exit /b 1
)

REM 检查 SF_API_KEY
if "%SF_API_KEY%"=="" (
    echo  [警告] 未检测到 SF_API_KEY 环境变量
    echo  AI 对比功能将无法使用，请在新窗口运行：
    echo    set SF_API_KEY=你的key
    echo    python service.py
    echo.
)

REM 检查依赖
python -c "import fastapi, uvicorn, anthropic" >nul 2>&1
if %errorlevel% neq 0 (
    echo  正在安装依赖 (fastapi uvicorn anthropic)...
    pip install fastapi uvicorn anthropic -q
)

REM 在新窗口启动 AI 服务 (8001)
if not "%SF_API_KEY%"=="" (
    echo  正在启动 AI 服务 (端口 8001)...
    start "eBay AI Service :8001" cmd /k "python service.py"
    timeout /t 2 /nobreak >nul
)

REM 启动静态文件服务器 (8080) 并打开浏览器
echo  正在启动前端服务器 (端口 8080)...
echo.
echo  请访问: http://localhost:8080
echo  按 Ctrl+C 停止
echo.
timeout /t 1 /nobreak >nul
start http://localhost:8080
cd /d "%~dp0"
python -m http.server 8080
