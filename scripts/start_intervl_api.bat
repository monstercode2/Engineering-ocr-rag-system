@echo off
echo ====================================
echo     启动 InterVL FastAPI 服务
echo ====================================

:: 设置环境变量
set PYTHONPATH=%PYTHONPATH%;E:\test\ocrsystem
set CUDA_VISIBLE_DEVICES=0

:: 检查Python环境
echo 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: Python未安装或未添加到PATH
    pause
    exit /b 1
)

:: 检查PyTorch是否可用
echo 检查PyTorch和CUDA...
python -c "import torch; print(f'PyTorch版本: {torch.__version__}'); print(f'CUDA可用: {torch.cuda.is_available()}')"
if %errorlevel% neq 0 (
    echo 警告: PyTorch检查失败，可能影响性能
)

:: 检查模型路径
echo 检查模型路径...
if not exist "E:\test\ocrsystem\models\internvl3-8b" (
    echo 错误: 模型路径不存在 E:\test\ocrsystem\models\internvl3-8b
    echo 请确保模型已正确下载到指定位置
    pause
    exit /b 1
)

:: 创建必要目录
echo 创建必要目录...
if not exist "E:\test\ocrsystem\data\temp" mkdir "E:\test\ocrsystem\data\temp"
if not exist "E:\test\ocrsystem\logs" mkdir "E:\test\ocrsystem\logs"

:: 切换到API目录
cd /d "E:\test\ocrsystem\api"

:: 检查依赖
echo 检查关键依赖...
python -c "import fastapi, uvicorn, transformers, torch, PIL; print('✅ 关键依赖检查通过')"
if %errorlevel% neq 0 (
    echo 错误: 关键依赖缺失，请安装requirements.txt
    echo 运行: pip install -r requirements.txt
    pause
    exit /b 1
)

:: 启动服务
echo ====================================
echo     启动 InterVL FastAPI 服务
echo     访问地址: http://localhost:8000
echo     API文档: http://localhost:8000/docs
echo     健康检查: http://localhost:8000/health
echo ====================================
echo.

python intervl_service.py

:: 如果服务异常退出
echo.
echo 服务已停止
pause 