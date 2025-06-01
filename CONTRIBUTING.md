# 贡献指南

感谢您对工程文档智能解析与RAG问答系统的关注！我们欢迎各种形式的贡献。

## 🚀 如何贡献

### 报告Bug
如果您发现了bug，请创建一个Issue并包含以下信息：
- 清晰的问题描述
- 重现步骤
- 期望的行为
- 实际的行为
- 您的环境信息（操作系统、Python版本等）
- 相关的错误日志

### 提出新功能
如果您有新功能的想法：
- 先创建一个Issue讨论您的想法
- 详细描述功能的用途和预期效果
- 如果可能，提供一些设计草图或示例

### 提交代码
1. Fork本仓库
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建一个Pull Request

## 📝 开发指南

### 环境设置
1. Fork并克隆仓库
2. 创建虚拟环境：`python -m venv venv`
3. 激活虚拟环境：`source venv/bin/activate`
4. 安装依赖：`pip install -r requirements.txt`
5. 安装开发依赖：`pip install -r dev-requirements.txt`

### 代码规范
- 使用Python PEP 8代码风格
- 函数和类应有适当的文档字符串
- 使用类型提示
- 保持代码简洁和可读性

### 测试
- 为新功能编写测试用例
- 确保所有测试通过：`pytest`
- 测试覆盖率应保持在80%以上

### 提交消息格式
使用以下格式的提交消息：
```
type(scope): description

[optional body]

[optional footer]
```

类型包括：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建或辅助工具的变动

### Pull Request指南
- 确保PR描述清晰地说明了所做的更改
- 链接相关的Issue
- 确保所有检查都通过
- 保持PR的大小合理，一个PR只解决一个问题

## 🏗️ 架构指南

### 项目结构
```
├── api/                # InterVL FastAPI服务
├── web/                # Flask Web应用
├── scripts/            # 部署和启动脚本
├── tests/              # 测试文件
├── docs/               # 文档
└── requirements.txt    # 项目依赖
```

### 关键组件
- **InterVL Service**: OCR处理服务
- **Flask Web App**: 用户界面和API网关
- **RAGFlow Integration**: RAG问答功能
- **File Management**: 文件上传和存储

## 🧪 测试指南

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_ocr_service.py

# 运行并生成覆盖率报告
pytest --cov=src
```

### 测试类型
- **单元测试**: 测试单个函数或类
- **集成测试**: 测试组件间的交互
- **端到端测试**: 测试完整的用户流程

## 📚 文档更新

如果您的更改涉及：
- 新的API端点
- 配置选项的变更
- 新功能或功能变更
- 安装或部署过程的变更

请确保更新相应的文档。

## 🔍 代码审查

所有提交的代码都会经过审查。审查重点包括：
- 代码质量和可读性
- 功能正确性
- 性能考虑
- 安全性
- 测试覆盖率
- 文档完整性

## 💡 开发技巧

### 调试
- 使用日志记录而不是print语句
- 设置适当的日志级别
- 使用调试器进行复杂问题的调试

### 性能优化
- 对于OCR处理，考虑批处理和异步操作
- 注意内存使用，特别是处理大文件时
- 使用缓存来减少重复计算

### 安全考虑
- 验证所有用户输入
- 安全地处理文件上传
- 保护API密钥和敏感配置

## 📋 发布流程

1. 更新版本号
2. 更新CHANGELOG.md
3. 创建release分支
4. 进行最终测试
5. 创建GitHub release
6. 更新文档

## 🤝 社区

- 尊重所有贡献者
- 保持友好和专业的交流
- 帮助新贡献者了解项目
- 鼓励知识分享

## ❓ 获取帮助

如果您需要帮助：
- 查看现有的Issues和Discussions
- 在Discussions中提问
- 通过Email联系维护者

感谢您的贡献！🎉 