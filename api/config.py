"""
InterVL FastAPI服务配置文件
"""

import os
from pathlib import Path

class Config:
    """服务配置类"""
    
    # 模型配置
    MODEL_PATH = r"E:\test\ocrsystem\models\internvl3-8b"
    MODEL_NAME = "internvl3-8b"
    
    # 服务配置
    HOST = "0.0.0.0"
    PORT = 8000
    WORKERS = 1  # GPU服务通常单进程
    LOG_LEVEL = "info"
    
    # 文件处理配置
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    TEMP_DIR = r"E:\test\ocrsystem\data\temp"
    SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".pdf", ".bmp", ".tiff"]
    
    # 模型推理配置
    MAX_NEW_TOKENS = 1024
    MAX_IMAGE_PATCHES = 12
    IMAGE_SIZE = 448
    
    # CORS配置
    CORS_ORIGINS = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:3000",  # 如果有React前端
        "http://127.0.0.1:3000"
    ]
    
    # 提示词配置
    DEFAULT_PROMPT = "请详细描述这张图片中的技术内容，包括图表、表格、文字和技术参数。"
    
    ENGINEERING_PROMPTS = {
        "general": "请详细描述这张图片中的技术内容，包括图表、表格、文字和技术参数。",
        "table": "请提取图片中的表格数据，包括标题、行列信息和具体数值。",
        "diagram": "请描述图片中的技术图表，包括流程、结构和关键要素。",
        "specification": "请提取图片中的技术规格和参数信息。"
    }
    
    @classmethod
    def get_prompt(cls, prompt_type: str = "general") -> str:
        """获取指定类型的提示词"""
        return cls.ENGINEERING_PROMPTS.get(prompt_type, cls.DEFAULT_PROMPT)
    
    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        Path(cls.TEMP_DIR).mkdir(parents=True, exist_ok=True)

# 开发环境配置
class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "debug"

# 生产环境配置  
class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = "warning"
    WORKERS = 1  # 根据GPU数量调整

# 根据环境变量选择配置
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': Config
}

def get_config(config_name=None):
    """获取配置对象"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    return config_map.get(config_name, Config) 