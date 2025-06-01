# InterVL FastAPI服务

基于InternVL3-8B模型的工程文档OCR解析服务，提供RESTful API接口供Flask前端调用。

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 确保模型已下载到指定位置
# E:\test\ocrsystem\models\internvl3-8b\
```

### 2. 启动服务

**Windows系统：**
```batch
# 使用启动脚本（推荐）
scripts\start_intervl_api.bat

# 或手动启动
cd api
python intervl_service.py
```

**Linux/Mac系统：**
```bash
cd api
python intervl_service.py
```

### 3. 验证服务

访问以下地址验证服务状态：
- 服务首页: http://localhost:8000
- API文档: http://localhost:8000/docs  
- 健康检查: http://localhost:8000/health

## 📡 API接口说明

### 1. 健康检查
```http
GET /health
```

**响应示例：**
```json
{
  "status": "healthy",
  "service": "InterVL OCR",
  "model": "internvl3-8b",
  "model_loaded": true,
  "device": "cuda",
  "gpu_available": true,
  "timestamp": "2025-01-27T10:30:00"
}
```

### 2. 模型信息
```http
GET /model/info
```

**响应示例：**
```json
{
  "model_name": "internvl3-8b",
  "model_path": "E:\\test\\ocrsystem\\models\\internvl3-8b",
  "device": "cuda",
  "is_loaded": true,
  "supported_formats": [".jpg", ".jpeg", ".png", ".pdf", ".bmp", ".tiff"],
  "max_file_size_mb": 50,
  "gpu_available": true
}
```

### 3. OCR文档处理 (核心接口)
```http
POST /ocr/process
```

**请求参数：**
- `file`: 上传的文件 (form-data)
- `prompt`: 可选的自定义提示词 (form-data)

**响应示例：**
```json
{
  "status": "success",
  "raw_text": "这是从图片中识别出的文本内容...",
  "confidence": 0.95,
  "metadata": {
    "model": "internvl3-8b",
    "device": "cuda",
    "prompt": "请详细描述这张图片中的技术内容...",
    "processing_time": 2.34,
    "image_patches": 6,
    "total_processing_time": 2.56
  },
  "structured_content": {
    "tables": [
      {
        "type": "detected_table",
        "content": "检测到表格内容",
        "confidence": 0.8
      }
    ],
    "diagrams": [],
    "annotations": [],
    "specifications": []
  },
  "file_info": {
    "filename": "technical_manual.jpg",
    "size": 1024576,
    "format": ".jpg",
    "image_size": "1920x1080"
  }
}
```

### 4. 批量处理
```http
POST /ocr/batch
```

**请求参数：**
- `files`: 多个上传文件 (form-data)
- `prompt`: 可选的自定义提示词 (form-data)

### 5. 重新加载模型
```http
POST /model/reload
```

## 🔧 配置说明

### 环境变量
```bash
# 设置模型路径
MODEL_PATH=E:\test\ocrsystem\models\internvl3-8b

# 设置设备
CUDA_VISIBLE_DEVICES=0

# 设置环境
FLASK_ENV=development
```

### 配置文件 (config.py)
```python
class Config:
    MODEL_PATH = r"E:\test\ocrsystem\models\internvl3-8b"
    HOST = "0.0.0.0"
    PORT = 8000
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".pdf", ".bmp", ".tiff"]
```

## 🧪 测试API

### 使用测试脚本
```bash
cd api
python test_api.py
```

### 使用curl测试
```bash
# 健康检查
curl http://localhost:8000/health

# OCR处理
curl -X POST "http://localhost:8000/ocr/process" \
     -F "file=@/path/to/image.jpg" \
     -F "prompt=请描述图片内容"
```

### 使用Python requests
```python
import requests

# OCR处理
with open('image.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/ocr/process',
        files={'file': f},
        data={'prompt': '请描述图片内容'}
    )
    result = response.json()
    print(result['raw_text'])
```

## 📊 性能优化

### GPU优化
- 自动检测CUDA可用性
- 支持bfloat16精度（GPU）
- Flash Attention加速（如果可用）

### 内存优化
- `low_cpu_mem_usage=True`
- 动态图片预处理
- 批量处理支持

### 并发处理
- FastAPI异步支持
- 单进程GPU服务（推荐）
- 支持多图片批量处理

## 🛠️ 故障排除

### 常见问题

1. **模型加载失败**
   ```
   FileNotFoundError: 模型路径不存在
   ```
   - 检查模型路径是否正确
   - 确保模型文件完整下载

2. **CUDA内存不足**
   ```
   RuntimeError: CUDA out of memory
   ```
   - 减少图片尺寸
   - 降低max_image_patches参数
   - 使用CPU模式

3. **依赖缺失**
   ```
   ModuleNotFoundError: No module named 'xxx'
   ```
   - 安装requirements.txt中的依赖
   - 检查PyTorch版本兼容性

### 日志查看
服务日志会输出到控制台，包含：
- 模型加载状态
- 请求处理时间
- 错误信息和堆栈跟踪

## 🔄 与Flask集成

Flask前端可以通过HTTP请求调用此API：

```python
# Flask中的调用示例
import requests

class InterVLAPIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def process_document(self, file_path):
        """调用InterVL API进行OCR处理"""
        with open(file_path, 'rb') as f:
            response = requests.post(
                f"{self.base_url}/ocr/process",
                files={"file": f}
            )
        return response.json()
```

## 📝 开发说明

### 项目结构
```
api/
├── intervl_service.py      # 主服务文件
├── config.py              # 配置文件
├── requirements.txt       # 依赖列表
├── test_api.py           # 测试脚本
└── README.md             # 说明文档
```

### 扩展接口
可以根据需要添加新的API端点：
1. 在`intervl_service.py`中添加新的路由
2. 实现相应的处理逻辑
3. 更新API文档

---

**🎯 注意**: 此服务专为工程文档OCR解析设计，基于InternVL3-8B多模态大模型，适用于复杂的技术文档、图表和规格表的智能识别。 