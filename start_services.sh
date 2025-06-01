#!/bin/bash

echo "========================================"
echo "工程文档智能解析与RAG问答系统"
echo "========================================"

echo ""
echo "正在启动服务..."

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "[1/3] 启动 InterVL FastAPI 服务..."
cd "$SCRIPT_DIR/api"
gnome-terminal --title="InterVL API Service" -- bash -c "python intervl_service.py; exec bash" 2>/dev/null || \
xterm -title "InterVL API Service" -e "python intervl_service.py" 2>/dev/null || \
python intervl_service.py &

echo ""
echo "[2/3] 启动 RAGFlow 服务..."
cd "$SCRIPT_DIR/ragflow"
gnome-terminal --title="RAGFlow Service" -- bash -c "docker-compose up; exec bash" 2>/dev/null || \
xterm -title "RAGFlow Service" -e "docker-compose up" 2>/dev/null || \
docker-compose up &

echo ""
echo "[3/3] 等待服务启动完成..."
sleep 15

echo ""
echo "启动 Flask Web 应用..."
cd "$SCRIPT_DIR/web"
gnome-terminal --title="Flask Web App" -- bash -c "python flask_app.py; exec bash" 2>/dev/null || \
xterm -title "Flask Web App" -e "python flask_app.py" 2>/dev/null || \
python flask_app.py &

echo ""
echo "========================================"
echo "所有服务已启动！"
echo ""
echo "访问地址:"
echo "- Web界面: http://localhost:5000"
echo "- InterVL API: http://localhost:8000"
echo "- RAGFlow: http://localhost:9380"
echo "========================================"

echo ""
echo "按 Ctrl+C 停止所有服务"
wait 