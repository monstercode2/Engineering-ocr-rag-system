"""
InterVL OCR API客户端

用于Flask Web应用调用InterVL FastAPI服务
"""

import requests
import json
import tempfile
import fitz  # PyMuPDF
import io
from PIL import Image
from pathlib import Path
from typing import Dict, Any, Optional, Union
import time
import logging

logger = logging.getLogger(__name__)

class InterVLAPIClient:
    """InterVL OCR API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        初始化API客户端
        
        Args:
            base_url: InterVL FastAPI服务的基础URL
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 300  # 5分钟超时
        
    def health_check(self) -> Dict[str, Any]:
        """检查API服务健康状态"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return {
                'success': True,
                'status': response.json(),
                'response_time': response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response_time': 0
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        try:
            response = self.session.get(f"{self.base_url}/model/info")
            response.raise_for_status()
            return {
                'success': True,
                'info': response.json()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_pdf_file(self, pdf_path: Union[str, Path], page_num: int = 0, 
                        prompt: str = None) -> Dict[str, Any]:
        """
        处理PDF文件进行OCR - 支持单页或全文档处理
        
        Args:
            pdf_path: PDF文件路径
            page_num: 页码（从0开始，-1表示处理所有页面）
            prompt: 自定义提示词
            
        Returns:
            OCR处理结果
        """
        try:
            # 如果page_num为-1，处理所有页面
            if page_num == -1:
                return self.process_full_pdf(pdf_path, prompt)
            
            # 否则处理单页
            # 1. 将PDF转换为图片
            image = self._pdf_to_image(pdf_path, page_num)
            if not image:
                return {
                    'success': False,
                    'error': 'PDF转换为图片失败'
                }
            
            # 2. 调用OCR API
            return self.process_image(image, prompt)
            
        except Exception as e:
            logger.error(f"PDF处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_full_pdf(self, pdf_path: Union[str, Path], prompt: str = None) -> Dict[str, Any]:
        """
        处理完整PDF的所有页面进行OCR
        
        Args:
            pdf_path: PDF文件路径
            prompt: 自定义提示词
            
        Returns:
            合并后的OCR处理结果
        """
        try:
            # 首先获取PDF页数
            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)
            doc.close()
            
            logger.info(f"开始处理PDF完整文档: {pdf_path}, 共 {total_pages} 页")
            
            all_text = []
            all_confidence = []
            all_tables = []
            all_processes = []
            all_annotations = []
            all_specifications = []
            total_processing_time = 0
            
            # 处理每一页
            for page_num in range(total_pages):
                logger.info(f"正在处理第 {page_num + 1}/{total_pages} 页...")
                
                # 转换当前页为图片
                image = self._pdf_to_image(pdf_path, page_num)
                if not image:
                    logger.warning(f"第 {page_num + 1} 页转换失败，跳过")
                    continue
                
                # 处理当前页
                page_result = self.process_image(image, prompt)
                
                if page_result.get('success'):
                    # 累积结果
                    page_text = page_result.get('raw_text', '')
                    if page_text.strip():
                        all_text.append(f"=== 第 {page_num + 1} 页 ===\n{page_text}")
                    
                    # 累积其他信息
                    if page_result.get('confidence'):
                        all_confidence.append(page_result['confidence'])
                    
                    if page_result.get('tables'):
                        all_tables.extend(page_result['tables'])
                    
                    if page_result.get('processes'):
                        all_processes.extend(page_result['processes'])
                    
                    if page_result.get('annotations'):
                        all_annotations.extend(page_result['annotations'])
                    
                    if page_result.get('specifications'):
                        all_specifications.extend(page_result['specifications'])
                    
                    total_processing_time += page_result.get('processing_time', 0)
                    
                    logger.info(f"第 {page_num + 1} 页处理完成，提取文本 {len(page_text)} 字符")
                else:
                    logger.warning(f"第 {page_num + 1} 页OCR处理失败: {page_result.get('error', '未知错误')}")
            
            # 合并所有结果
            combined_text = '\n\n'.join(all_text)
            avg_confidence = sum(all_confidence) / len(all_confidence) if all_confidence else 0
            
            result = {
                'success': True,
                'raw_text': combined_text,
                'confidence': avg_confidence,
                'tables': all_tables,
                'processes': all_processes,
                'annotations': all_annotations,
                'specifications': all_specifications,
                'processing_time': total_processing_time,
                'total_pages': total_pages,
                'processed_pages': len(all_text),
                'metadata': {
                    'pages_processed': len(all_text),
                    'total_pages': total_pages,
                    'avg_confidence': avg_confidence,
                    'total_chars': len(combined_text)
                }
            }
            
            logger.info(f"PDF完整处理完成: {total_pages} 页，提取文本 {len(combined_text)} 字符")
            return result
            
        except Exception as e:
            logger.error(f"完整PDF处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_image_file(self, image_path: Union[str, Path], 
                          prompt: str = None) -> Dict[str, Any]:
        """
        处理图片文件进行OCR
        
        Args:
            image_path: 图片文件路径
            prompt: 自定义提示词
            
        Returns:
            OCR处理结果
        """
        try:
            with open(image_path, 'rb') as f:
                return self._call_ocr_api(f, prompt)
        except Exception as e:
            logger.error(f"图片处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_image(self, image: Image.Image, prompt: str = None) -> Dict[str, Any]:
        """
        处理PIL图片对象进行OCR
        
        Args:
            image: PIL图片对象
            prompt: 自定义提示词
            
        Returns:
            OCR处理结果
        """
        try:
            # 保存为临时文件
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                image.save(temp_file.name, 'JPEG', quality=95)
                temp_path = temp_file.name
            
            try:
                # 调用OCR API
                with open(temp_path, 'rb') as f:
                    result = self._call_ocr_api(f, prompt)
                return result
            finally:
                # 清理临时文件
                Path(temp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"图片处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_batch_files(self, file_paths: list, prompt: str = None) -> Dict[str, Any]:
        """
        批量处理文件
        
        Args:
            file_paths: 文件路径列表
            prompt: 自定义提示词
            
        Returns:
            批量处理结果
        """
        try:
            files_data = []
            for file_path in file_paths:
                path = Path(file_path)
                if path.suffix.lower() == '.pdf':
                    # PDF文件需要先转换
                    image = self._pdf_to_image(file_path, 0)
                    if image:
                        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                            image.save(temp_file.name, 'JPEG', quality=95)
                            with open(temp_file.name, 'rb') as f:
                                files_data.append(('files', f.read()))
                            Path(temp_file.name).unlink(missing_ok=True)
                else:
                    # 图片文件直接读取
                    with open(file_path, 'rb') as f:
                        files_data.append(('files', f.read()))
            
            data = {}
            if prompt:
                data['prompt'] = prompt
                
            response = self.session.post(
                f"{self.base_url}/ocr/batch", 
                files=files_data,
                data=data
            )
            response.raise_for_status()
            
            return {
                'success': True,
                'results': response.json()
            }
            
        except Exception as e:
            logger.error(f"批量处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _pdf_to_image(self, pdf_path: Union[str, Path], page_num: int = 0) -> Optional[Image.Image]:
        """使用PyMuPDF将PDF转换为图片"""
        try:
            doc = fitz.open(str(pdf_path))
            
            if page_num >= len(doc):
                logger.error(f"页码 {page_num} 超出范围，PDF共 {len(doc)} 页")
                return None
            
            page = doc[page_num]
            
            # 使用高分辨率渲染
            mat = fitz.Matrix(2.0, 2.0)  # 2倍缩放
            pix = page.get_pixmap(matrix=mat)
            
            # 转换为PIL Image
            img_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(img_data))
            
            doc.close()
            return image
            
        except Exception as e:
            logger.error(f"PDF转换失败: {e}")
            return None
    
    def _call_ocr_api(self, file_obj, prompt: str = None) -> Dict[str, Any]:
        """调用OCR API"""
        try:
            start_time = time.time()
            
            files = {"file": file_obj}
            data = {}
            
            if prompt:
                data["prompt"] = prompt
            else:
                data["prompt"] = "请详细提取这个文档中的文字内容，包括标题、正文、表格和技术参数。重点关注文档的主要内容和结构。"
            
            response = self.session.post(
                f"{self.base_url}/ocr/process",
                files=files,
                data=data
            )
            
            processing_time = time.time() - start_time
            response.raise_for_status()
            
            result = response.json()
            result['api_processing_time'] = processing_time
            result['success'] = True
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API调用失败: {e}")
            return {
                'success': False,
                'error': f'API调用失败: {str(e)}'
            }
        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# 创建全局实例
intervl_client = InterVLAPIClient()

def get_intervl_client() -> InterVLAPIClient:
    """获取InterVL API客户端实例"""
    return intervl_client 