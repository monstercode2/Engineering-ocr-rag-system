@echo off
echo ========================================
echo 工程文档智能解析与RAG问答系统
echo ========================================

echo.
echo 正在启动服务...

echo.
echo [1/3] 启动 InterVL FastAPI 服务...
cd /d "%~dp0api"
start "InterVL API Service" cmd /k "python intervl_service.py"

echo.
echo [2/3] 启动 RAGFlow 服务...
cd /d "%~dp0ragflow"
start "RAGFlow Service" cmd /k "docker-compose up"

echo.
echo [3/3] 等待服务启动完成...
timeout /t 15 /nobreak

echo.
echo 启动 Flask Web 应用...
cd /d "%~dp0web"
start "Flask Web App" cmd /k "python flask_app.py"

echo.
echo ========================================
echo 所有服务已启动！
echo.
echo 访问地址:
echo - Web界面: http://localhost:5000
echo - InterVL API: http://localhost:8000
echo - RAGFlow: http://localhost:9380
echo ========================================

pause 