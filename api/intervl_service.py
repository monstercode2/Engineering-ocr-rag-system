"""
InterVL FastAPI服务

提供InterVL多模态大模型的OCR服务
基于官方InternVL3-8B模型，通过FastAPI对外提供RESTful接口
"""

import os
import io
import json
import torch
import asyncio
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from transformers import AutoTokenizer, AutoModel
from PIL import Image
import uvicorn

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="InterVL OCR Service",
    description="基于InternVL3-8B的工程文档OCR解析服务",
    version="1.0.0"
)

# CORS设置 - 允许Flask前端调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局配置
CONFIG = {
    "MODEL_PATH": r"E:\test\ocrsystem\models\internvl3-8b",
    "DEVICE": "cuda" if torch.cuda.is_available() else "cpu",
    "MAX_FILE_SIZE": 500 * 1024 * 1024,  # 500MB (增加文件大小限制)
    "SUPPORTED_FORMATS": [".jpg", ".jpeg", ".png", ".pdf", ".bmp", ".tiff"],
    "DEFAULT_PROMPT": "请详细描述这张图片中的技术内容，包括图表、表格、文字和技术参数，并且不要遗漏任何一个字或者一处内容。",
}

def build_transform(input_size):
    """构建图片预处理变换"""
    from torchvision import transforms
    transform = transforms.Compose([
        transforms.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        transforms.Resize((input_size, input_size), interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225))
    ])
    return transform

def dynamic_preprocess(image, image_size, use_thumbnail=False, max_num=12):
    """动态预处理图片"""
    orig_width, orig_height = image.size
    aspect_ratio = orig_width / orig_height

    # 计算目标尺寸
    target_ratios = set(
        (i, j) for n in range(1, max_num + 1) for i in range(1, n + 1) for j in range(1, n + 1) if
        i * j <= max_num and i * j >= 1
    )
    target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])

    # 找到最接近的比例
    target_aspect_ratio = find_closest_aspect_ratio(
        aspect_ratio, target_ratios, orig_width, orig_height, image_size)

    # 计算目标宽度和高度
    target_width = image_size * target_aspect_ratio[0]
    target_height = image_size * target_aspect_ratio[1]
    blocks = target_aspect_ratio[0] * target_aspect_ratio[1]

    # 调整图片大小并分割
    resized_img = image.resize((target_width, target_height))
    processed_images = []
    for i in range(blocks):
        box = (
            (i % (target_width // image_size)) * image_size,
            (i // (target_width // image_size)) * image_size,
            ((i % (target_width // image_size)) + 1) * image_size,
            ((i // (target_width // image_size)) + 1) * image_size
        )
        # 分割图片
        split_img = resized_img.crop(box)
        processed_images.append(split_img)

    # 如果使用缩略图，添加原图的缩略图
    if use_thumbnail and len(processed_images) != 1:
        thumbnail = image.resize((image_size, image_size))
        processed_images.append(thumbnail)

    return processed_images

def find_closest_aspect_ratio(aspect_ratio, target_ratios, width, height, image_size):
    """找到最接近的宽高比"""
    best_ratio_diff = float('inf')
    best_ratio = (1, 1)
    area = width * height
    for ratio in target_ratios:
        target_aspect_ratio = ratio[0] / ratio[1]
        ratio_diff = abs(aspect_ratio - target_aspect_ratio)
        if ratio_diff < best_ratio_diff:
            best_ratio_diff = ratio_diff
            best_ratio = ratio
        elif ratio_diff == best_ratio_diff:
            if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                best_ratio = ratio
    return best_ratio

def load_image(image, input_size=448, max_num=12):
    """加载和预处理图片"""
    transform = build_transform(input_size=input_size)
    images = dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
    pixel_values = [transform(img) for img in images]
    pixel_values = torch.stack(pixel_values)
    return pixel_values

class InterVLModelManager:
    """InterVL模型管理器"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_path = Path(CONFIG["MODEL_PATH"])
        self.device = CONFIG["DEVICE"]
        self.is_loaded = False
        
    def load_model(self):
        """加载InternVL模型"""
        try:
            logger.info(f"开始加载InterVL模型: {self.model_path}")
            logger.info(f"使用设备: {self.device}")
            
            # 检查模型路径
            if not self.model_path.exists():
                raise FileNotFoundError(f"模型路径不存在: {self.model_path}")
            
            # 加载tokenizer
            logger.info("加载tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_path), 
                trust_remote_code=True
            )
            
            # 加载模型
            logger.info("加载模型...")
            if self.device == "cuda":
                self.model = AutoModel.from_pretrained(
                    str(self.model_path),
                    torch_dtype=torch.bfloat16,
                    low_cpu_mem_usage=True,
                    use_flash_attn=True,
                    trust_remote_code=True
                ).eval().cuda()
            else:
                # CPU模式
                self.model = AutoModel.from_pretrained(
                    str(self.model_path),
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True,
                    trust_remote_code=True
                ).eval()
            
            self.is_loaded = True
            logger.info("✅ InterVL模型加载成功")
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            self.is_loaded = False
            raise e
    
    def process_image(self, image: Image.Image, prompt: Optional[str] = None) -> Dict[str, Any]:
        """处理图片，返回OCR结果"""
        if not self.is_loaded:
            raise RuntimeError("模型未加载")
        
        try:
            start_time = datetime.now()
            
            # 使用默认提示词或自定义提示词
            if prompt is None:
                prompt = CONFIG["DEFAULT_PROMPT"]
            
            # 图片预处理
            pixel_values = load_image(image, max_num=12)
            pixel_values = pixel_values.to(self.device)
            if self.device == "cuda":
                pixel_values = pixel_values.to(torch.bfloat16)
            
            # 生成配置
            generation_config = dict(max_new_tokens=1024, do_sample=False)
            
            # 调用模型进行推理
            question = f'<image>\n{prompt}'
            
            with torch.no_grad():
                response, history = self.model.chat(
                    self.tokenizer, 
                    pixel_values, 
                    question, 
                    generation_config,
                    history=None, 
                    return_history=True
                )
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 解析结构化内容（简单示例）
            structured_content = self._parse_structured_content(response)
            
            # 构建返回结果
            result = {
                "status": "success",
                "raw_text": response,
                "confidence": 0.95,  # InterVL没有直接的置信度输出，这里设置固定值
                "metadata": {
                    "model": "internvl3-8b",
                    "device": self.device,
                    "prompt": prompt,
                    "processing_time": processing_time,
                    "image_patches": pixel_values.shape[0]
                },
                "structured_content": structured_content
            }
            
            logger.info(f"✅ 图片处理完成，耗时: {processing_time:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"❌ 图片处理失败: {e}")
            raise e
    
    def _parse_structured_content(self, text: str) -> Dict[str, List]:
        """简单解析结构化内容"""
        try:
            # 这里可以实现更复杂的结构化解析逻辑
            # 目前只是简单的关键词匹配
            
            tables = []
            diagrams = []
            annotations = []
            specifications = []
            
            # 检测表格相关内容
            if any(keyword in text.lower() for keyword in ['表格', '数据', '参数', '指标']):
                tables.append({
                    "type": "detected_table",
                    "content": "检测到表格内容",
                    "confidence": 0.8
                })
            
            # 检测图表相关内容
            if any(keyword in text.lower() for keyword in ['图', '图表', '示意图', '流程']):
                diagrams.append({
                    "type": "detected_diagram",
                    "content": "检测到图表内容",
                    "confidence": 0.8
                })
            
            # 检测技术规格
            if any(keyword in text.lower() for keyword in ['规格', '参数', '技术指标', '性能']):
                specifications.append({
                    "type": "technical_specs",
                    "content": "检测到技术规格",
                    "confidence": 0.8
                })
            
            return {
                "tables": tables,
                "diagrams": diagrams,
                "annotations": annotations,
                "specifications": specifications
            }
            
        except Exception as e:
            logger.warning(f"结构化内容解析失败: {e}")
            return {
                "tables": [],
                "diagrams": [],
                "annotations": [],
                "specifications": []
            }

# 全局模型管理器实例
model_manager = InterVLModelManager()

@app.on_event("startup")
async def startup_event():
    """应用启动时加载模型"""
    try:
        logger.info("🚀 启动InterVL OCR服务...")
        model_manager.load_model()
        logger.info("🎉 服务启动完成")
    except Exception as e:
        logger.error(f"❌ 服务启动失败: {e}")
        # 可以选择继续启动但标记为不可用状态

@app.get("/")
async def root():
    """根路径 - 服务信息"""
    return {
        "service": "InterVL OCR Service",
        "version": "1.0.0",
        "model": "internvl3-8b",
        "status": "ready" if model_manager.is_loaded else "loading",
        "device": CONFIG["DEVICE"],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy" if model_manager.is_loaded else "unhealthy",
        "service": "InterVL OCR",
        "model": "internvl3-8b",
        "model_loaded": model_manager.is_loaded,
        "device": CONFIG["DEVICE"],
        "gpu_available": torch.cuda.is_available(),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/ocr/process")
async def process_document(
    file: UploadFile = File(...),
    prompt: Optional[str] = None
):
    """
    处理上传的文档/图片，进行OCR识别
    
    参数:
    - file: 上传的文件（图片或PDF）
    - prompt: 可选的自定义提示词
    
    返回:
    - OCR识别结果，包含文本、结构化内容等
    """
    try:
        # 验证模型状态
        if not model_manager.is_loaded:
            raise HTTPException(
                status_code=503, 
                detail="模型未加载，请稍后重试"
            )
        
        # 验证文件大小
        if file.size and file.size > CONFIG["MAX_FILE_SIZE"]:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大支持 {CONFIG['MAX_FILE_SIZE'] // (1024*1024)}MB"
            )
        
        # 验证文件格式
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in CONFIG["SUPPORTED_FORMATS"]:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_ext}，支持: {CONFIG['SUPPORTED_FORMATS']}"
            )
        
        # 读取文件内容
        file_content = await file.read()
        
        # 转换为PIL图片
        try:
            image = Image.open(io.BytesIO(file_content))
            # 转换为RGB模式（如果不是的话）
            if image.mode != 'RGB':
                image = image.convert('RGB')
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"无法打开图片文件: {e}"
            )
        
        # 记录处理开始
        start_time = datetime.now()
        logger.info(f"开始处理文件: {file.filename}")
        
        # 调用模型处理
        result = model_manager.process_image(image, prompt)
        
        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds()
        result["metadata"]["total_processing_time"] = processing_time
        
        # 添加文件信息
        result["file_info"] = {
            "filename": file.filename,
            "size": file.size,
            "format": file_ext,
            "image_size": f"{image.width}x{image.height}"
        }
        
        logger.info(f"✅ 文件处理完成: {file.filename}, 耗时: {processing_time:.2f}秒")
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 处理文档时出错: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@app.post("/ocr/batch")
async def batch_process_documents(
    files: List[UploadFile] = File(...),
    prompt: Optional[str] = None
):
    """
    批量处理多个文档
    """
    try:
        if not model_manager.is_loaded:
            raise HTTPException(status_code=503, detail="模型未加载")
        
        if len(files) > 10:  # 限制批量处理数量
            raise HTTPException(status_code=400, detail="批量处理最多支持10个文件")
        
        results = []
        for file in files:
            try:
                # 重用单文件处理逻辑
                file_content = await file.read()
                image = Image.open(io.BytesIO(file_content))
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                result = model_manager.process_image(image, prompt)
                result["file_info"] = {
                    "filename": file.filename,
                    "size": file.size
                }
                results.append(result)
                
            except Exception as e:
                results.append({
                    "status": "error",
                    "filename": file.filename,
                    "error": str(e)
                })
        
        return JSONResponse(content={
            "status": "completed",
            "total_files": len(files),
            "results": results
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 批量处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量处理失败: {str(e)}")

@app.get("/model/info")
async def get_model_info():
    """获取模型信息"""
    return {
        "model_name": "internvl3-8b",
        "model_path": str(CONFIG["MODEL_PATH"]),
        "device": CONFIG["DEVICE"],
        "is_loaded": model_manager.is_loaded,
        "supported_formats": CONFIG["SUPPORTED_FORMATS"],
        "max_file_size_mb": CONFIG["MAX_FILE_SIZE"] // (1024 * 1024),
        "gpu_available": torch.cuda.is_available(),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/model/reload")
async def reload_model():
    """重新加载模型"""
    try:
        logger.info("🔄 重新加载模型...")
        model_manager.load_model()
        return {
            "status": "success",
            "message": "模型重新加载成功",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ 模型重新加载失败: {e}")
        raise HTTPException(status_code=500, detail=f"模型重新加载失败: {str(e)}")

if __name__ == "__main__":
    # 启动服务
    logger.info("🚀 启动InterVL FastAPI服务...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # 生产环境建议关闭
        log_level="info"
    ) 