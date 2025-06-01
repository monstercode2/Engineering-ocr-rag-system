# 🚀 RAGFlow API 接口总结

## 📋 概述

RAGFlow提供了完整的RESTful API，可以通过HTTP调用来实现文档处理、知识库管理、聊天对话等功能。以下是我们项目中可以使用的主要API接口。

## 🔑 认证方式

所有API调用都需要在HTTP请求头中包含API密钥：
```
Authorization: Bearer <YOUR_API_KEY>
Content-Type: application/json
```

## 📚 主要API接口分类

### 1. 数据集(Knowledge Base)管理 API

#### 创建数据集
- **POST** `/api/v1/datasets`
- **功能**: 创建新的知识库数据集
- **参数**:
  - `name`: 数据集名称
  - `description`: 数据集描述  
  - `chunk_method`: 分块方法 (naive, qa, paper, book, etc.)
  - `embedding_model`: 嵌入模型
- **返回**: 数据集ID和详细信息

#### 获取数据集列表
- **GET** `/api/v1/datasets`
- **功能**: 获取所有数据集列表
- **参数**: page, page_size, orderby, desc
- **返回**: 数据集列表和总数

#### 更新数据集
- **PUT** `/api/v1/datasets/{dataset_id}`
- **功能**: 更新数据集配置
- **参数**: name, description, embedding_model, etc.

#### 删除数据集
- **DELETE** `/api/v1/datasets`
- **功能**: 删除指定数据集
- **参数**: `ids` (数据集ID数组)

### 2. 文档管理 API

#### 上传文档
- **POST** `/api/v1/datasets/{dataset_id}/documents`
- **功能**: 上传文档到指定数据集
- **参数**: 文件对象 (multipart/form-data)
- **支持格式**: PDF, Word, TXT, Excel, PPT等

#### 获取文档列表
- **GET** `/api/v1/datasets/{dataset_id}/documents`
- **功能**: 获取数据集中的文档列表
- **参数**: page, page_size, keywords, orderby

#### 删除文档
- **DELETE** `/api/v1/datasets/{dataset_id}/documents`
- **功能**: 删除指定文档
- **参数**: `ids` (文档ID数组)

#### 解析文档
- **POST** `/api/v1/datasets/{dataset_id}/chunks`
- **功能**: 解析文档并生成知识块
- **参数**: `document_ids` (文档ID数组)

### 3. 聊天助手管理 API

#### 创建聊天助手
- **POST** `/api/v1/chats`
- **功能**: 创建基于数据集的聊天助手
- **参数**:
  - `name`: 助手名称
  - `dataset_ids`: 关联的数据集ID列表
  - `description`: 助手描述
  - `llm`: LLM配置
  - `prompt`: 提示词配置

#### 获取聊天助手列表
- **GET** `/api/v1/chats`
- **功能**: 获取所有聊天助手
- **参数**: page, page_size, name, orderby

#### 更新聊天助手
- **PUT** `/api/v1/chats/{chat_id}`
- **功能**: 更新聊天助手配置

#### 删除聊天助手
- **DELETE** `/api/v1/chats`
- **功能**: 删除聊天助手

### 4. 会话管理 API

#### 创建会话
- **POST** `/api/v1/chats/{chat_id}/sessions`
- **功能**: 为聊天助手创建新会话
- **参数**: 
  - `name`: 会话名称
  - `user_id`: 用户ID (可选)

#### 获取会话列表
- **GET** `/api/v1/chats/{chat_id}/sessions`
- **功能**: 获取聊天助手的所有会话

#### 更新会话
- **PUT** `/api/v1/chats/{chat_id}/sessions/{session_id}`
- **功能**: 更新会话信息

#### 删除会话
- **DELETE** `/api/v1/chats/{chat_id}/sessions`
- **功能**: 删除会话

### 5. 对话 API (OpenAI兼容)

#### 聊天对话
- **POST** `/api/v1/chats_openai/{chat_id}/chat/completions`
- **功能**: 与聊天助手进行对话 (兼容OpenAI API格式)
- **参数**:
  - `model`: 模型名称 (任意值)
  - `messages`: 消息历史数组
  - `stream`: 是否流式响应 (true/false)
- **返回**: 聊天回复 (支持流式和非流式)

### 6. 搜索检索 API

#### 知识检索
- **POST** `/api/v1/retrieval`
- **功能**: 从知识库中检索相关信息
- **参数**:
  - `kb_id`: 数据集ID
  - `question`: 查询问题
- **返回**: 相关知识块和相似度分数

## 🛠️ 在我们项目中的应用场景

### 1. OCR结果处理流程
```python
# 1. 创建或获取数据集
POST /api/v1/datasets
{
    "name": "工程文档集",
    "description": "OCR处理后的工程文档",
    "chunk_method": "naive",
    "embedding_model": "BAAI/bge-large-zh-v1.5@BAAI"
}

# 2. 上传OCR提取的文本内容作为文档
POST /api/v1/datasets/{dataset_id}/documents
# 上传文本文件或直接传递OCR结果

# 3. 解析文档生成知识块
POST /api/v1/datasets/{dataset_id}/chunks
{
    "document_ids": ["doc_id_1", "doc_id_2"]
}
```

### 2. 智能问答流程
```python
# 1. 创建聊天助手
POST /api/v1/chats
{
    "name": "工程文档助手",
    "dataset_ids": ["dataset_id_1"],
    "description": "基于工程文档的智能助手"
}

# 2. 创建会话
POST /api/v1/chats/{chat_id}/sessions
{
    "name": "工程咨询会话"
}

# 3. 进行对话
POST /api/v1/chats_openai/{chat_id}/chat/completions
{
    "model": "ragflow",
    "messages": [
        {"role": "user", "content": "这个设备的技术参数是什么？"}
    ],
    "stream": false
}
```

### 3. 知识检索流程
```python
# 直接从知识库检索相关信息
POST /api/v1/retrieval
{
    "kb_id": "dataset_id",
    "question": "设备维护周期"
}
```

## 🔧 集成建议

### 1. 环境配置
```bash
# 在.env文件中设置
RAGFLOW_API_KEY=your_api_key_here
RAGFLOW_BASE_URL=http://localhost:9380
```

### 2. Python客户端使用
```python
from web.utils.ragflow_api_client import get_ragflow_client

# 获取客户端实例
client = get_ragflow_client()

# 检查服务状态
health = client.health_check()

# 创建数据集
dataset = client.create_dataset("我的数据集", "描述")

# 上传文档内容
result = client.upload_text_content(
    dataset_id, 
    ocr_text, 
    "document.txt"
)

# 创建聊天助手
chat = client.create_chat_assistant(
    "助手名称", 
    [dataset_id]
)

# 进行对话
answer = client.simple_chat(chat_id, "用户问题")
```

## 📝 注意事项

1. **API密钥管理**: 确保API密钥的安全存储，不要在代码中硬编码
2. **错误处理**: 所有API调用都应包含适当的错误处理
3. **流量控制**: 注意API调用频率限制
4. **数据格式**: 确保上传的文档格式符合要求
5. **权限控制**: 每个API调用都有权限验证，确保当前用户有相应权限

## 🚀 性能优化

1. **批量操作**: 尽量使用批量API减少网络请求
2. **缓存机制**: 对常用的数据集和聊天助手信息进行缓存
3. **异步处理**: 对于大文件上传和解析，使用异步方式处理
4. **流式响应**: 对于长对话，使用流式API提供更好的用户体验

这些API接口为我们的工程文档智能解析系统提供了强大的RAG问答能力！🎯 