@echo off
chcp 65001 >nul
title Stock Data Web Server

echo 🚀 正在启动股票数据Web服务器...
echo.

REM 设置默认的API密钥 (请修改为你自己的密钥)
set DEFAULT_API_KEY=sk-stock-data-2024-abcd1234efgh5678

REM 你可以通过环境变量覆盖默认密钥
if defined STOCK_API_KEY (
    set API_KEY=%STOCK_API_KEY%
) else (
    set API_KEY=%DEFAULT_API_KEY%
)

REM 其他配置参数
set SERVER_PORT=8888
set SERVER_HOST=0.0.0.0
set DEBUG_MODE=

echo 🔐 使用API密钥: %API_KEY:~0,8%...
echo 📡 服务端口: %SERVER_PORT%
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 检查是否需要安装依赖
if not exist "venv\" (
    echo 📦 创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo 📥 安装依赖包...
    pip install flask flask-cors pandas
) else (
    echo 🔄 激活虚拟环境...
    call venv\Scripts\activate.bat
)

echo 🌐 启动Web服务器...
echo 📡 服务地址: http://localhost:%SERVER_PORT%
echo 🔑 认证方式:
echo    - Bearer Token: Authorization: Bearer %API_KEY%
echo    - Query参数: ?api_key=%API_KEY%
echo    - Web登录: 浏览器访问后输入API密钥
echo 🛑 按 Ctrl+C 停止服务器
echo.

REM 启动服务器，如果需要调试模式，取消下面的注释
REM python WebServer.py --api-key "%API_KEY%" --port %SERVER_PORT% --host %SERVER_HOST% --debug
python WebServer.py --api-key "%API_KEY%" --port %SERVER_PORT% --host %SERVER_HOST%

pause 