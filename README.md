# 🚀 工程文档智能解析与RAG问答系统

基于InterVL和RAGFlow的现代化工程文档智能解析与RAG问答系统。该系统专门针对复杂工程文档（技术说明书、设计图纸、标注文档）进行OCR识别和智能问答。

## ✨ 核心特性

### 🔍 强大的OCR能力
- **InterVL多模态OCR**: 基于先进的视觉语言模型，支持复杂工程文档解析
- **多格式支持**: PDF、Word、图片格式（JPG、PNG、TIFF）等
- **结构化提取**: 自动识别表格、图表、标注、技术规格等元素
- **高精度识别**: 针对工程文档优化的OCR算法

### 🤖 智能RAG问答
- **RAGFlow集成**: 本地部署的企业级RAG解决方案
- **领域专精**: 专门针对工程技术文档的问答优化
- **上下文理解**: 基于文档内容的智能推理和回答
- **多轮对话**: 支持连续的技术咨询对话

### 🏗️ 微服务架构
- **InterVL FastAPI服务**: 高性能OCR处理服务
- **Flask Web前端**: 现代化的用户界面
- **RAGFlow本地服务**: 独立的RAG问答服务
- **服务分离**: 各组件独立部署，易于扩展

### 💼 工程领域适配
- **多领域支持**: 机械、电气、化工、土木、航空航天等
- **文档类型识别**: 自动识别技术手册、工程图纸、工艺流程图等
- **专业术语处理**: 针对工程技术术语的优化处理

## 🎯 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                   Flask Web Frontend                           │
│              (用户界面和API网关)                                   │
├─────────────────────────────────────────────────────────────────┤
│                    Service Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ InterVL FastAPI │  │ RAGFlow Service │  │   File Storage  │ │
│  │   (OCR服务)      │  │ (本地RAG服务)    │  │   (文档存储)     │ │
│  │   :8000         │  │   :9380         │  │   Local FS      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      Model Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  InterVL Model  │  │ RAGFlow Vector  │  │  Raw Documents  │ │
│  │ internvl3-8b    │  │    Database     │  │   Storage       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠️ 技术栈

### 后端技术
- **Python 3.8+**: 主要开发语言
- **FastAPI**: InterVL OCR服务API框架
- **Flask**: Web前端框架
- **PyTorch**: 深度学习框架
- **Transformers**: Hugging Face模型库

### 前端技术
- **Bootstrap 5**: 响应式UI框架
- **JavaScript ES6+**: 前端交互逻辑
- **Socket.IO**: 实时通信
- **Font Awesome**: 图标库

### AI模型
- **InterVL3-8B**: 多模态视觉语言模型
- **RAGFlow**: 企业级RAG解决方案

## 📦 安装指南

### 环境要求
- Python 3.8+
- CUDA 11.8+ (推荐使用GPU)
- 至少16GB内存
- 至少10GB磁盘空间

### 1. 克隆项目
```bash
git clone https://github.com/your-username/engineering-ocr-rag-system.git
cd engineering-ocr-rag-system
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或者
venv\Scripts\activate     # Windows
```

### 3. 安装依赖
```bash
# 安装FastAPI服务依赖
pip install -r api/requirements.txt

# 安装主项目依赖
pip install -r requirements.txt
```

### 4. 下载模型
```bash
# 创建模型目录
mkdir -p models

# 下载InterVL3-8B模型 (需要约15GB空间)
# 方法1: 使用Git LFS
git lfs clone https://huggingface.co/OpenGVLab/InternVL2-8B models/internvl3-8b

# 方法2: 使用huggingface-hub
pip install huggingface-hub
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='OpenGVLab/InternVL2-8B', local_dir='models/internvl3-8b')"
```

### 5. 配置RAGFlow
```bash
# 部署RAGFlow (需要Docker)
git clone https://github.com/infiniflow/ragflow.git
cd ragflow
docker-compose up -d
```

### 6. 环境变量配置
```bash
# 创建.env文件
cp .env.example .env

# 编辑.env文件，设置API密钥等
RAGFLOW_API_KEY=your_ragflow_api_key
RAGFLOW_BASE_URL=http://localhost:9380
```

## 🚀 快速开始

### 1. 启动InterVL FastAPI服务
```bash
cd api
python intervl_service.py
# 服务将在 http://localhost:8000 启动
```

### 2. 启动RAGFlow服务
```bash
cd ragflow
docker-compose up -d
# 服务将在 http://localhost:9380 启动
```

### 3. 启动Flask Web应用
```bash
cd web
python flask_app.py
# 应用将在 http://localhost:5000 启动
```

### 4. 访问系统
打开浏览器访问 `http://localhost:5000` 开始使用系统。

## 📚 使用指南

### 文档上传与OCR处理
1. 访问"文档上传"页面
2. 拖拽或选择工程文档文件
3. 点击"处理"按钮进行OCR识别
4. 查看识别结果和结构化数据

### 添加到知识库
1. OCR处理完成后，点击"添加到知识库"
2. 系统自动将文档内容上传到RAGFlow
3. 文档将被向量化并存储在知识库中

### 智能问答
1. 访问"智能问答"页面
2. 输入关于工程文档的问题
3. 系统基于知识库内容生成答案
4. 支持多轮对话和上下文理解

## 🔧 API文档

### InterVL OCR API
- `GET /health` - 健康检查
- `POST /ocr/process` - 单文件OCR处理
- `POST /ocr/batch` - 批量OCR处理
- `GET /model/info` - 模型信息

### Flask Web API
- `GET /api/system/status` - 系统状态
- `POST /api/upload` - 文件上传
- `POST /api/ocr/process` - OCR处理
- `POST /api/knowledge/add` - 添加到知识库
- `POST /api/chat/query` - 智能问答

详细API文档请参考各服务的README文件。

## 🏗️ 项目结构

```
engineering-ocr-rag-system/
├── api/                    # InterVL FastAPI服务
│   ├── intervl_service.py  # 主服务文件
│   ├── config.py           # 配置文件
│   ├── requirements.txt    # 依赖列表
│   └── README.md           # API服务文档
├── web/                    # Flask Web应用
│   ├── flask_app.py        # 主应用文件
│   ├── templates/          # HTML模板
│   ├── static/             # 静态资源
│   ├── utils/              # 工具模块
│   └── README.md           # Web应用文档
├── scripts/                # 启动脚本
│   └── start_intervl_api.bat
├── tests/                  # 测试文件
├── requirements.txt        # 主项目依赖
├── 架构设计.md              # 详细架构设计文档
├── .gitignore              # Git忽略文件
└── README.md               # 项目说明文档
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与项目。

### 贡献方式
- 🐛 报告Bug
- 💡 提出新功能建议
- 📝 改进文档
- 💻 提交代码

### 开发流程
1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目基于MIT许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [InterVL](https://github.com/OpenGVLab/InternVL) - 强大的多模态视觉语言模型
- [RAGFlow](https://github.com/infiniflow/ragflow) - 企业级RAG解决方案
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化API框架
- [Flask](https://flask.palletsprojects.com/) - 轻量级Web框架

## 📞 支持与联系

如果您在使用过程中遇到问题或有任何建议，请通过以下方式联系我们：

- 🐛 Issues: [GitHub Issues](https://github.com/your-username/engineering-ocr-rag-system/issues)

## ⭐ Star History

如果这个项目对您有帮助，请给我们一个Star⭐！

[![Star History Chart](https://api.star-history.com/svg?repos=your-username/engineering-ocr-rag-system&type=Date)](https://star-history.com/#your-username/engineering-ocr-rag-system&Date)

---

**AI让工程文档解析变得更加智能！** 
