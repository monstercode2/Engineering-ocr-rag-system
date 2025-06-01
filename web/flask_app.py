"""
工程文档智能解析与RAG问答系统 - Flask Web应用

现代化的Flask前端，替代Streamlit
提供RESTful API和现代化的用户界面
"""

from flask import Flask, render_template, request, jsonify, session, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from werkzeug.utils import secure_filename

# 导入我们的核心模块
try:
    # 使用简化的InterVL API客户端
    from utils.intervl_api_client import get_intervl_client
    # 导入RAGFlow API客户端
    from utils.ragflow_api_client import get_ragflow_client, set_ragflow_api_key
    # 保留其他导入作为可选
    from ..rag.intervl_ragflow_adapter import InterVLRAGFlowAdapter
    from ..rag.ragflow_client import RealRAGFlowClient
    from ..config.settings import settings
    from ..utils.logger import get_logger
    from ..utils.file_utils import validate_file, get_file_info, calculate_file_hash
except ImportError as e:
    # 开发环境导入 - 使用简化的方式
    from utils.intervl_api_client import get_intervl_client
    from utils.ragflow_api_client import get_ragflow_client, set_ragflow_api_key
    
    # 日志配置简化
    import logging
    
    def get_logger(name):
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    # 简化的文件工具函数
    def validate_file(file_path):
        return Path(file_path).exists()
    
    def get_file_info(file_path):
        path = Path(file_path)
        stat = path.stat()
        return {
            'name': path.name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime)
        }
    
    def calculate_file_hash(file_path):
        import hashlib
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-please-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# 启用CORS支持
CORS(app)

# 启用SocketIO支持（用于实时通信）
socketio = SocketIO(app, cors_allowed_origins="*")

# 配置日志
logger = get_logger(__name__)

# 全局变量
ragflow_adapter = None
intervl_client = None  # 改为使用API客户端
ragflow_client = None  # 添加RAGFlow API客户端
upload_folder = Path(__file__).parent / "data" / "uploads"  # 修复为绝对路径
upload_folder.mkdir(parents=True, exist_ok=True)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.docx', '.doc'}

def init_systems():
    """初始化OCR和RAG系统"""
    global ragflow_adapter, intervl_client, ragflow_client
    
    try:
        logger.info("🚀 开始初始化系统...")
        
        # 初始化InterVL API客户端
        logger.info("⚙️ 正在初始化InterVL API客户端...")
        intervl_client = get_intervl_client()
        
        # 检查API服务状态
        health = intervl_client.health_check()
        if health['success']:
            logger.info("✅ InterVL API服务连接成功")
        else:
            logger.warning(f"⚠️ InterVL API服务连接失败: {health['error']}")
            logger.info("💡 系统将以降级模式运行，OCR功能暂不可用")
        
        # 初始化RAGFlow API客户端（自动从环境变量读取API密钥）
        logger.info("🔧 正在初始化RAGFlow API客户端...")
        ragflow_client = get_ragflow_client()
        
        # 检查是否从环境变量成功读取了API密钥
        env_api_key = os.getenv('RAGFLOW_API_KEY')
        if env_api_key:
            logger.info(f"✅ 从环境变量读取到RAGFlow API密钥: {env_api_key[:20]}...")
            # 确保客户端使用环境变量中的API密钥
            ragflow_client.set_api_key(env_api_key)
        else:
            logger.warning("⚠️ 环境变量中未找到RAGFLOW_API_KEY，请检查.env文件")
        
        # 检查RAGFlow服务状态
        rag_health = ragflow_client.health_check()
        if rag_health['success']:
            logger.info("✅ RAGFlow API服务连接成功")
        else:
            logger.warning(f"⚠️ RAGFlow API服务连接失败: {rag_health['error']}")
            if 'API密钥' in str(rag_health.get('error', '')):
                logger.info("💡 提示：请检查.env文件中的RAGFLOW_API_KEY是否正确设置")
            logger.info("💡 系统将以降级模式运行，RAG功能暂不可用")
        
        # 初始化RAGFlow适配器（可选，保持兼容性）
        try:
            logger.info("🔧 正在初始化RAGFlow适配器...")
            # ragflow_adapter = InterVLRAGFlowAdapter()
            logger.info("✅ RAGFlow适配器初始化跳过（使用API模式）")
        except Exception as rag_error:
            logger.warning(f"⚠️ RAGFlow适配器初始化失败: {rag_error}")
        
        logger.info("🎉 系统初始化完成！核心组件已就绪")
        return True
        
    except Exception as e:
        logger.error(f"❌ 系统初始化失败: {e}")
        # 记录详细错误信息
        import traceback
        logger.error(f"详细错误:\n{traceback.format_exc()}")
        return False

def allowed_file(filename):
    """检查文件是否允许上传"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

# ==================== 主页面路由 ====================

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/chat')
def chat_page():
    """聊天页面"""
    return render_template('chat.html')

@app.route('/upload')
def upload_page():
    """文件上传页面"""
    return render_template('upload.html')

@app.route('/knowledge')
def knowledge_page():
    """知识库管理页面"""
    return render_template('knowledge.html')

@app.route('/settings')
def settings_page():
    """系统设置页面"""
    return render_template('settings.html')

@app.route('/ragflow')
def ragflow_management_page():
    """RAGFlow管理页面 - 模仿RAGFlow后台界面"""
    return render_template('ragflow_management.html')

# ==================== 静态文件处理 ====================

@app.route('/favicon.ico')
def favicon():
    """处理favicon请求"""
    # 返回一个简单的透明PNG图标
    from flask import make_response
    import base64
    
    # 1x1透明PNG图片的base64编码
    transparent_png = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
    )
    
    response = make_response(transparent_png)
    response.headers['Content-Type'] = 'image/png'
    response.headers['Cache-Control'] = 'max-age=86400'  # 缓存1天
    return response

@app.route('/robots.txt')
def robots():
    """处理robots.txt请求"""
    from flask import make_response
    
    robots_content = """User-agent: *
Disallow: /api/
Disallow: /admin/
Allow: /"""
    
    response = make_response(robots_content)
    response.headers['Content-Type'] = 'text/plain'
    return response

# ==================== API接口 ====================

@app.route('/api/system/status')
def system_status():
    """获取系统状态"""
    global ragflow_adapter, intervl_client, ragflow_client
    
    # 检查InterVL API服务状态
    if intervl_client:
        api_health = intervl_client.health_check()
    else:
        api_health = {'success': False, 'error': 'API客户端未初始化'}
    
    # 检查RAGFlow API服务状态
    if ragflow_client:
        rag_health = ragflow_client.health_check()
    else:
        rag_health = {'success': False, 'error': 'RAGFlow客户端未初始化'}
    
    status = {
        'timestamp': datetime.now().isoformat(),
        'ragflow_adapter': ragflow_adapter is not None,
        'ocr_manager': api_health['success'],  # 基于API状态
        'intervl_api': api_health,
        'ragflow_api': rag_health,
        'upload_folder': str(upload_folder),
        'allowed_extensions': list(ALLOWED_EXTENSIONS)
    }
    
    if ragflow_adapter:
        try:
            # 获取RAGFlow状态
            ragflow_status = ragflow_adapter.get_system_status()
            status['ragflow'] = ragflow_status
        except Exception as e:
            status['ragflow'] = {'error': str(e)}
    else:
        status['ragflow'] = {'error': 'RAGFlow未初始化，当前使用API模式'}
    
    return jsonify(status)

@app.route('/api/system/init', methods=['POST'])
def init_system():
    """初始化系统"""
    success = init_systems()
    return jsonify({
        'success': success,
        'message': '系统初始化成功' if success else '系统初始化失败',
        'timestamp': datetime.now().isoformat()
    })

# ==================== 文件上传API ====================

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """文件上传接口"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有选择文件',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '没有选择文件',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'不支持的文件类型，支持的格式: {", ".join(ALLOWED_EXTENSIONS)}',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # 保存文件 - 重写文件名处理逻辑
        original_filename = file.filename
        
        # 手动清理文件名，避免secure_filename过度清理
        import re
        # 保留字母、数字、点号、下划线、中文字符
        clean_filename = re.sub(r'[^\w\.\u4e00-\u9fff-]', '_', original_filename)
        
        # 如果文件名被完全清空，使用默认名称
        if not clean_filename or clean_filename == '.pdf' or clean_filename.startswith('.'):
            clean_filename = f"document_{int(time.time())}.pdf"
        
        timestamp = int(time.time())
        unique_filename = f"{timestamp}_{clean_filename}"
        file_path = upload_folder / unique_filename
        
        # 确保上传目录存在
        upload_folder.mkdir(parents=True, exist_ok=True)
        
        # 保存文件并验证
        try:
            file.save(str(file_path))
            
            # 验证文件是否真的保存成功
            if not file_path.exists():
                raise Exception(f"文件保存失败，文件不存在: {file_path}")
            
            # 验证文件大小
            if file_path.stat().st_size == 0:
                raise Exception(f"文件保存失败，文件大小为0: {file_path}")
                
            logger.info(f"文件保存成功: {file_path} (大小: {file_path.stat().st_size} 字节)")
        
        except Exception as save_error:
            logger.error(f"文件保存失败: {save_error}")
            # 清理可能的空文件
            if file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
            return jsonify({
                'success': False,
                'error': f'文件保存失败: {str(save_error)}',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        # 获取文件信息
        try:
            file_info = get_file_info(str(file_path))
            file_hash = calculate_file_hash(str(file_path))
        except Exception as e:
            logger.warning(f"获取文件信息失败: {e}")
            file_info = {'size': file_path.stat().st_size if file_path.exists() else 0}
            file_hash = 'unknown'
        
        result = {
            'success': True,
            'filename': clean_filename,
            'unique_filename': unique_filename,
            'file_path': f"data/uploads/{unique_filename}",  # 返回相对路径
            'absolute_path': str(file_path),  # 添加绝对路径供调试使用
            'file_size': file_info.get('size', 0),
            'file_hash': file_hash,
            'upload_time': datetime.now().isoformat(),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"文件上传成功: {clean_filename}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/files')
def get_uploaded_files():
    """获取已上传文件列表"""
    try:
        # 确保上传目录存在
        upload_folder.mkdir(parents=True, exist_ok=True)
        
        files = []
        for file_path in upload_folder.glob('*'):
            if file_path.is_file():
                try:
                    stat = file_path.stat()
                    files.append({
                        'filename': file_path.name,
                        'size': stat.st_size,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2),
                        'modified_time': stat.st_mtime,
                        'modified_time_str': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'document_type': identify_document_type(file_path.name),
                        'engineering_domain': estimate_engineering_domain(file_path.name)
                    })
                except Exception as e:
                    logger.warning(f"获取文件信息失败 {file_path.name}: {e}")
                    continue
        
        # 按修改时间排序
        files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return jsonify({
            'success': True,
            'files': files,
            'total': len(files),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'files': [],
            'total': 0,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    """删除单个文件"""
    try:
        # 安全检查：确保文件名不包含路径遍历
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({
                'success': False,
                'error': '无效的文件名',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        file_path = upload_folder / filename
        
        # 检查文件是否存在
        if not file_path.exists():
            return jsonify({
                'success': False,
                'error': '文件不存在',
                'timestamp': datetime.now().isoformat()
            }), 404
        
        # 检查是否为文件（不是目录）
        if not file_path.is_file():
            return jsonify({
                'success': False,
                'error': '指定路径不是文件',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # 删除文件
        file_path.unlink()
        
        logger.info(f"文件删除成功: {filename}")
        
        return jsonify({
            'success': True,
            'message': f'文件 {filename} 删除成功',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"删除文件失败 {filename}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/files/clear', methods=['POST'])
def clear_all_files():
    """清空所有上传的文件"""
    try:
        deleted_count = 0
        error_count = 0
        
        # 遍历上传目录中的所有文件
        for file_path in upload_folder.glob('*'):
            if file_path.is_file():
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"删除文件: {file_path.name}")
                except Exception as e:
                    error_count += 1
                    logger.warning(f"删除文件失败 {file_path.name}: {e}")
        
        # 返回结果
        if error_count == 0:
            message = f"成功清空所有文件，共删除 {deleted_count} 个文件"
            logger.info(message)
        else:
            message = f"清空完成，成功删除 {deleted_count} 个文件，{error_count} 个文件删除失败"
            logger.warning(message)
        
        return jsonify({
            'success': True,
            'message': message,
            'deleted_count': deleted_count,
            'error_count': error_count,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"清空文件失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'deleted_count': 0,
            'error_count': 0,
            'timestamp': datetime.now().isoformat()
        }), 500
        
# ==================== OCR处理API ====================

@app.route('/api/ocr/process', methods=['POST'])
def process_ocr():
    """OCR处理接口"""
    global intervl_client
    
    try:
        # 检查InterVL API客户端是否初始化
        if not intervl_client:
            return jsonify({
                'success': False,
                'error': 'InterVL API客户端未初始化，请先初始化系统',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据格式错误',
                'timestamp': datetime.now().isoformat()
            }), 400
            
        file_path = data.get('file_path')
        
        # 处理文件路径 - 支持相对路径和绝对路径
        if not file_path:
            return jsonify({
                'success': False,
                'error': '文件路径不能为空',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # 如果是相对路径，转换为绝对路径
        if not Path(file_path).is_absolute():
            # 相对于Flask应用的根目录
            abs_file_path = Path(__file__).parent / file_path
        else:
            abs_file_path = Path(file_path)
        
        # 检查文件是否存在
        if not abs_file_path.exists():
            logger.error(f"文件不存在: {abs_file_path}")
            return jsonify({
                'success': False,
                'error': f'文件不存在: {file_path}',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # 执行OCR处理
        try:
            # 检查API服务状态
            health = intervl_client.health_check()
            if not health['success']:
                return jsonify({
                    'success': False,
                    'error': f'❌ InterVL API服务不可用: {health["error"]}',
                    'timestamp': datetime.now().isoformat()
                }), 503
            
            # 根据文件类型调用相应的处理方法
            file_ext = Path(abs_file_path).suffix.lower()
            if file_ext == '.pdf':
                # 处理完整PDF的所有页面
                result = intervl_client.process_pdf_file(str(abs_file_path), page_num=-1)
            else:
                result = intervl_client.process_image_file(str(abs_file_path))
            
            if not result['success']:
                return jsonify({
                    'success': False,
                    'error': f'❌ OCR处理失败: {result["error"]}',
                    'timestamp': datetime.now().isoformat()
                }), 500
            
            logger.info(f"OCR处理完成，识别文本长度: {len(result.get('raw_text', ''))}")
            
            # 格式化结果
            ocr_result = {
                'success': True,
                'file_path': str(abs_file_path),
                'text': result.get('raw_text', ''),
                'confidence': result.get('confidence', 0),
                'technical_tables': result.get('tables', []),
                'process_diagrams': result.get('processes', []),
                'annotations': result.get('annotations', []),
                'specifications': result.get('specifications', []),
                'processing_time': result.get('processing_time', 0),
                'api_processing_time': result.get('api_processing_time', 0),
                'metadata': result.get('metadata', {}),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ OCR处理成功: {abs_file_path}")
            return jsonify(ocr_result)
            
        except Exception as ocr_error:
            logger.error(f"❌ OCR处理失败: {ocr_error}")
            return jsonify({
                'success': False,
                'error': str(ocr_error),
                'timestamp': datetime.now().isoformat()
            }), 500
        
    except Exception as e:
        logger.error(f"❌ OCR处理失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ==================== RAG问答API ====================

@app.route('/api/chat/query', methods=['POST'])
def chat_query():
    """智能问答接口"""
    global ragflow_adapter
    
    try:
        if not ragflow_adapter:
            return jsonify({
                'success': False,
                'message': 'RAG系统未初始化，请先初始化系统',
                'answer': '抱歉，智能问答系统尚未初始化。请联系管理员或稍后重试。',
                'confidence': 0,
                'sources': [],
                'processing_time': 0,
                'timestamp': datetime.now().isoformat()
            })
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据格式错误',
                'timestamp': datetime.now().isoformat()
            }), 400
            
        question = data.get('question', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not question:
            return jsonify({
                'success': False,
                'error': '问题不能为空',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # 执行RAG查询
        response = ragflow_adapter.query(
            question=question,
            session_id=session_id,
            max_documents=5
        )
        
        result = {
            'success': True,
            'session_id': session_id,
            'question': question,
            'answer': response.get('answer', ''),
            'confidence': response.get('confidence', 0),
            'sources': response.get('sources', []),
            'processing_time': response.get('processing_time', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"问答处理完成: {question[:50]}...")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"问答处理失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'answer': '抱歉，处理您的问题时遇到了错误。请稍后重试。',
            'confidence': 0,
            'sources': [],
            'processing_time': 0,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/chat/history/<session_id>')
def get_chat_history(session_id):
    """获取聊天历史"""
    # 这里可以从数据库或文件中读取聊天历史
    # 暂时返回空列表
    return jsonify({
        'session_id': session_id,
        'messages': [],
        'timestamp': datetime.now().isoformat()
    })

# ==================== 知识库管理API ====================

@app.route('/api/knowledge/stats')
def knowledge_stats():
    """获取知识库统计信息"""
    global ragflow_client
    
    try:
        if not ragflow_client:
            return jsonify({
                'success': False,
                'message': 'RAGFlow API客户端未初始化',
                'stats': {
                    'total_documents': 0,
                    'total_chunks': 0,
                    'storage_size': 0,
                    'last_updated': None
                },
                'timestamp': datetime.now().isoformat()
            })
        
        # 获取数据集列表来统计信息
        datasets_response = ragflow_client.list_datasets()
        
        if datasets_response['success']:
            datasets = datasets_response.get('data', [])
            total_documents = len(datasets)
            
            # 计算总文档数和存储大小
            total_chunks = 0
            storage_size = 0
            last_updated = None
            
            for dataset in datasets:
                # 累计知识片段数量（假设每个数据集有多个chunk）
                chunk_num = dataset.get('chunk_num', 0)
                if chunk_num:
                    total_chunks += chunk_num
                
                # 累计存储大小
                doc_num = dataset.get('document_amount', 0)
                if doc_num:
                    storage_size += doc_num * 1024 * 1024  # 假设每个文档平均1MB
                
                # 找最新更新时间
                update_time = dataset.get('update_time')
                if update_time:
                    if not last_updated or update_time > last_updated:
                        last_updated = update_time
            
            stats = {
                'total_documents': total_documents,
                'total_chunks': total_chunks,
                'storage_size': storage_size,
                'last_updated': last_updated
            }
        else:
            stats = {
                'total_documents': 0,
                'total_chunks': 0,
                'storage_size': 0,
                'last_updated': None
            }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取知识库统计失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {
                'total_documents': 0,
                'total_chunks': 0,
                'storage_size': 0,
                'last_updated': None
            },
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/knowledge/documents')
def get_knowledge_documents():
    """获取知识库文档列表"""
    global ragflow_client
    
    try:
        if not ragflow_client:
            return jsonify({
                'success': False,
                'message': 'RAGFlow API客户端未初始化',
                'documents': [],
                'total': 0,
                'timestamp': datetime.now().isoformat()
            })
        
        # 获取数据集列表
        datasets_response = ragflow_client.list_datasets()
        
        if not datasets_response['success']:
            return jsonify({
                'success': False,
                'message': f'获取数据集列表失败: {datasets_response.get("error", "未知错误")}',
                'documents': [],
                'total': 0,
                'timestamp': datetime.now().isoformat()
            })
        
        datasets = datasets_response.get('data', [])
        documents = []
        
        # 将数据集转换为文档格式
        for dataset in datasets:
            document = {
                'id': dataset.get('id'),
                'name': dataset.get('name', '未知数据集'),
                'type': identify_document_type(dataset.get('name', '')),
                'domain': estimate_engineering_domain(dataset.get('name', '')),
                'created_at': dataset.get('create_time'),
                'updated_at': dataset.get('update_time'),
                'size': dataset.get('document_amount', 0) * 1024 * 1024,  # 估算大小
                'chunks': dataset.get('chunk_num', 0),
                'status': 'processed' if dataset.get('chunk_num', 0) > 0 else 'processing',
                'description': dataset.get('description', ''),
                'parser_id': dataset.get('parser_id'),
                'avatar': dataset.get('avatar')
            }
            documents.append(document)
        
        return jsonify({
            'success': True,
            'documents': documents,
            'total': len(documents),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'documents': [],
            'total': 0,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/knowledge/add', methods=['POST'])
def add_to_knowledge_base():
    """添加文档到知识库"""
    global ragflow_client
    
    try:
        if not ragflow_client:
            return jsonify({
                'success': False,
                'message': 'RAGFlow API客户端未初始化',
                'timestamp': datetime.now().isoformat()
            })
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据格式错误',
                'timestamp': datetime.now().isoformat()
            }), 400
            
        file_path = data.get('file_path')
        ocr_result = data.get('ocr_result')
        dataset_id = data.get('dataset_id')
        dataset_name = data.get('dataset_name')
        create_new = data.get('create_new', False)
        
        logger.info(f"接收到知识库添加请求: file_path={file_path}, ocr_result长度={len(ocr_result) if ocr_result else 0}, create_new={create_new}")
        
        # 检查是否提供了OCR结果
        if not ocr_result or not ocr_result.strip():
            return jsonify({
                'success': False,
                'error': '❌ 未提供OCR结果。请先点击"处理"按钮进行OCR识别，然后再添加到知识库。',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        logger.info(f"准备添加到知识库: OCR结果长度={len(ocr_result)}, 文件路径={file_path}")
        
        # 如果需要创建新知识库
        if create_new:
            dataset_description = data.get('dataset_description', '')
            parser_config = data.get('parser_config', {})
            embedding_model = data.get('embedding_model', 'BAAI/bge-large-zh-v1.5@BAAI')
            
            # 默认知识库名称
            if not dataset_name:
                dataset_name = "工程文档知识库"
            
            logger.info(f"准备创建数据集: {dataset_name}")
            
            # 🔍 首先检查是否已存在同名数据集
            logger.info("检查是否存在同名数据集...")
            existing_dataset_id = None
            datasets_response = ragflow_client.list_datasets()
            
            if datasets_response['success']:
                datasets_list = datasets_response['data']
                if isinstance(datasets_list, list):
                    for dataset in datasets_list:
                        if dataset['name'] == dataset_name:
                            existing_dataset_id = dataset['id']
                            logger.info(f"✅ 发现已存在的数据集: {dataset_name} (ID: {existing_dataset_id})")
                            break
            
            if existing_dataset_id:
                # 使用已存在的数据集
                dataset_id = existing_dataset_id
                logger.info(f"♻️ 复用已存在的数据集: {dataset_name}")
            else:
                # 创建新数据集
                logger.info(f"🆕 创建新数据集: {dataset_name}")
                logger.info(f"解析器配置: {parser_config}")
                logger.info(f"嵌入模型: {embedding_model}")
                
                # 构建解析器配置
                if parser_config:
                    # 用户提供了具体配置
                    final_parser_config = {
                        "chunk_token_num": parser_config.get('chunk_token_num', 128),
                        "layout_recognize": parser_config.get('layout_recognize', 'DeepDOC'),
                        "delimiter": parser_config.get('delimiter', '\\n'),
                        "html4excel": parser_config.get('html4excel', False),
                        "raptor": {"use_raptor": False},
                        "filename_embd_weight": parser_config.get('filename_embd_weight', 0.1)
                    }
                    # 🔧 额外检查：如果filename_embd_weight为None，设置为默认值
                    if final_parser_config["filename_embd_weight"] is None:
                        final_parser_config["filename_embd_weight"] = 0.1
                        logger.info("检测到filename_embd_weight为None，已设置为默认值0.1")
                else:
                    # 使用默认配置，确保filename_embd_weight有效
                    final_parser_config = {
                        "chunk_token_num": 128,
                        "layout_recognize": "DeepDOC", 
                        "delimiter": "\\n",
                        "html4excel": False,
                        "raptor": {"use_raptor": False},
                        "filename_embd_weight": 0.1
                    }
                
                create_params = {
                    'name': dataset_name,
                    'description': dataset_description or f"工程文档OCR处理结果，创建于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    'chunk_method': parser_config.get('chunk_method', 'naive'),
                    'embedding_model': embedding_model,
                    'permission': 'me',
                    'parser_config': final_parser_config
                }
                
                logger.info(f"创建数据集参数: {create_params}")
                
                dataset_response = ragflow_client.create_dataset(**create_params)
                
                if not dataset_response['success']:
                    error_msg = dataset_response.get('error', '未知错误')
                    logger.error(f"创建数据集失败: {error_msg}")
                    
                    # 如果是名称冲突错误，尝试生成唯一名称
                    if 'already exists' in error_msg.lower() or '已存在' in error_msg:
                        logger.info("⚠️ 检测到名称冲突，尝试生成唯一名称...")
                        unique_name = f"{dataset_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        create_params['name'] = unique_name
                        logger.info(f"🔄 使用唯一名称重试: {unique_name}")
                        
                        dataset_response = ragflow_client.create_dataset(**create_params)
                        
                        if not dataset_response['success']:
                            return jsonify({
                                'success': False,
                                'error': f"创建数据集失败: {dataset_response.get('error', '未知错误')}",
                                'timestamp': datetime.now().isoformat()
                            }), 500
                        
                        dataset_name = unique_name  # 更新数据集名称
                    else:
                        return jsonify({
                            'success': False,
                            'error': f"创建数据集失败: {error_msg}",
                            'timestamp': datetime.now().isoformat()
                        }), 500
                    
                dataset_id = dataset_response['data']['id']
                logger.info(f"✅ 数据集创建成功: {dataset_name} (ID: {dataset_id})")
            
        else:
            # 使用已有知识库
            if not dataset_id:
                # 如果没有指定数据集ID，则查找或创建默认数据集
                if not dataset_name:
                    dataset_name = "工程文档知识库"
                    
                # 首先检查是否已有同名数据集
                datasets_response = ragflow_client.list_datasets()
                existing_dataset_id = None
                
                if datasets_response['success']:
                    datasets_list = datasets_response['data']
                    if isinstance(datasets_list, list):
                        for dataset in datasets_list:
                            if dataset['name'] == dataset_name:
                                existing_dataset_id = dataset['id']
                                logger.info(f"找到现有数据集: {dataset_name} (ID: {existing_dataset_id})")
                                break
                    else:
                        logger.warning(f"数据集列表格式异常: {type(datasets_list)}")
                else:
                    logger.warning(f"获取数据集列表失败: {datasets_response.get('error')}")
                
                if existing_dataset_id:
                    dataset_id = existing_dataset_id
                else:
                    # 创建默认数据集
                    logger.info(f"创建默认数据集: {dataset_name}")
                    dataset_response = ragflow_client.create_dataset(
                        name=dataset_name,
                        chunk_method="naive",
                        description=f"工程文档OCR处理结果，创建于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    
                    if not dataset_response['success']:
                        error_msg = dataset_response.get('error', '未知错误')
                        logger.error(f"创建数据集失败: {error_msg}")
                        return jsonify({
                            'success': False,
                            'error': f"创建数据集失败: {error_msg}",
                            'timestamp': datetime.now().isoformat()
                        }), 500
                        
                    dataset_id = dataset_response['data']['id']
                    logger.info(f"数据集创建成功: {dataset_name} (ID: {dataset_id})")
        
        # 上传OCR内容到数据集
        filename = f"ocr_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        if file_path:
            original_name = Path(file_path).stem
            filename = f"{original_name}_ocr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        logger.info(f"开始上传文档内容到数据集 {dataset_id}, 文件名: {filename}")
        
        upload_response = ragflow_client.upload_text_content(
            dataset_id=dataset_id,
            content=ocr_result,
            filename=filename
        )
        
        if upload_response['success']:
            logger.info(f"文档上传成功: {upload_response}")
            
            # 🚀 **关键步骤：文档上传后立即开始解析处理**
            document_id = upload_response.get('document_id')
            if document_id:
                logger.info(f"🔧 开始解析文档: {document_id}")
                
                # 调用解析API开始解析
                parse_response = ragflow_client.parse_documents(
                    dataset_id=dataset_id,
                    document_ids=[document_id]
                )
                
                if parse_response['success']:
                    logger.info(f"✅ 文档解析启动成功: {parse_response['message']}")
                    parse_message = f"✅ 文档已成功添加到知识库并开始解析处理"
                else:
                    logger.warning(f"⚠️ 文档解析启动失败: {parse_response.get('error')}")
                    parse_message = f"⚠️ 文档已添加到知识库，但解析启动失败: {parse_response.get('error')}"
            else:
                logger.warning("⚠️ 上传响应中未找到document_id，无法启动解析")
                parse_message = "⚠️ 文档已添加到知识库，但无法获取文档ID启动解析"
        
        return jsonify({
            'success': True,
            'result': {
                'dataset_id': dataset_id,
                'dataset_name': dataset_name,
                'document_id': document_id,
                'filename': filename,
                'content_length': len(ocr_result),
                'created_new': create_new,
                'parse_started': document_id is not None and parse_response.get('success', False)
            },
            'message': parse_message,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"添加到知识库失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ==================== WebSocket实时通信 ====================

@socketio.on('connect')
def handle_connect():
    """WebSocket连接处理"""
    emit('status', {'message': '连接成功', 'timestamp': datetime.now().isoformat()})
    logger.info(f"用户连接: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket断开处理"""
    logger.info(f"用户断开: {request.sid}")

@socketio.on('process_file')
def handle_file_processing(data):
    """处理文件上传和OCR识别"""
    global intervl_client, ragflow_adapter
    
    try:
        file_path = data.get('file_path')
        filename = data.get('filename', '未知文件')
        
        # 发送开始处理消息
        emit('processing_update', {
            'status': 'started',
            'message': f'开始处理文件: {filename}',
            'progress': 0
        })
        
        # 检查InterVL API客户端状态
        if not intervl_client:
            emit('processing_update', {
                'status': 'error',
                'message': '❌ InterVL API客户端未初始化',
                'progress': 0
            })
            return
        
        # 发送OCR处理中消息
        emit('processing_update', {
            'status': 'ocr_processing',
            'message': '🔍 正在进行OCR识别...',
            'progress': 20
        })
        
        # 执行OCR处理
        try:
            # 检查API服务状态
            health = intervl_client.health_check()
            if not health['success']:
                emit('processing_update', {
                    'status': 'error',
                    'message': f'❌ InterVL API服务不可用: {health["error"]}',
                    'progress': 0
                })
                return
            
            # 根据文件类型调用相应的处理方法
            file_ext = Path(file_path).suffix.lower()
            if file_ext == '.pdf':
                # 处理完整PDF的所有页面
                result = intervl_client.process_pdf_file(str(file_path), page_num=-1)
            else:
                result = intervl_client.process_image_file(str(file_path))
            
            if not result['success']:
                emit('processing_update', {
                    'status': 'error',
                    'message': f'❌ OCR处理失败: {result["error"]}',
                    'progress': 0
                })
                return
            
            emit('processing_update', {
                'status': 'ocr_completed',
                'message': f'✅ OCR识别完成，提取 {len(result.get("raw_text", ""))} 字符',
                'progress': 60,
                'ocr_result': {
                    'text': result.get('raw_text', ''),
                    'confidence': result.get('confidence', 0),
                    'metadata': result.get('metadata', {})
                }
            })
        except Exception as ocr_error:
            emit('processing_update', {
                'status': 'error',
                'message': f'❌ InterVL解析失败: {str(ocr_error)}',
                'progress': 0
            })
            return
        
        # 检查RAGFlow适配器状态
        if not ragflow_adapter:
            emit('processing_update', {
                'status': 'warning',
                'message': '⚠️ RAGFlow适配器未初始化，无法添加到知识库',
                'progress': 80
            })
        else:
            # 发送知识库添加中消息
            emit('processing_update', {
                'status': 'rag_processing',
                'message': '📚 正在添加到知识库...',
                'progress': 80
            })
            
            # 添加到知识库
            try:
                rag_result = ragflow_adapter.process_document(file_path)
                
                emit('processing_update', {
                    'status': 'rag_completed',
                    'message': '✅ 成功添加到知识库',
                    'progress': 100,
                    'rag_result': rag_result
                })
            except Exception as rag_error:
                emit('processing_update', {
                    'status': 'warning',
                    'message': f'⚠️ 文档上传失败: {str(rag_error)}',
                    'progress': 80
                })
        
        # 发送最终完成消息
        emit('processing_update', {
            'status': 'completed',
            'message': '🎉 文件处理完成！',
            'progress': 100
        })
        
    except Exception as e:
        logger.error(f"❌ 端到端处理失败: {e}")
        emit('processing_update', {
            'status': 'error',
            'message': f'❌ 端到端处理失败: {str(e)}',
            'progress': 0
        })

# ==================== 辅助函数 ====================

def identify_document_type(filename: str) -> str:
    """识别文档类型"""
    ext = Path(filename).suffix.lower()
    mapping = {
        '.pdf': 'technical_manual',
        '.docx': 'technical_manual',
        '.doc': 'technical_manual',
        '.jpg': 'engineering_drawing',
        '.jpeg': 'engineering_drawing',
        '.png': 'engineering_drawing',
        '.bmp': 'engineering_drawing',
        '.tiff': 'engineering_drawing'
    }
    return mapping.get(ext, 'general')

def estimate_engineering_domain(filename: str) -> str:
    """估算工程领域"""
    filename_lower = filename.lower()
    
    domain_keywords = {
        'mechanical': ['机械', '设备', '零件', 'mechanical', 'equipment', 'part', 'motor'],
        'electrical': ['电气', '电路', '电机', 'electrical', 'circuit', 'electric'],
        'chemical': ['化工', '反应', '工艺', 'chemical', 'process', 'reaction'],
        'civil': ['土木', '建筑', '结构', 'civil', 'building', 'structure'],
        'aerospace': ['航空', '航天', 'aerospace', 'aviation', 'flight']
    }
    
    for domain, keywords in domain_keywords.items():
        if any(keyword in filename_lower for keyword in keywords):
            return domain
    
    return 'general'

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, error_message='页面未找到'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, error_message='服务器内部错误'), 500

# ==================== RAGFlow真实API管理 ====================

@app.route('/api/ragflow/datasets/overview')
def get_datasets_overview():
    """获取RAGFlow数据集概览 - 基于真实API"""
    try:
        ragflow_client = get_ragflow_client()
        
        # 调用真实的RAGFlow API获取数据集列表
        datasets_response = ragflow_client.list_datasets()
        
        if not datasets_response['success']:
            return jsonify({
                'success': False,
                'error': f'获取数据集失败: {datasets_response["error"]}',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        # 使用真实数据进行统计
        datasets = datasets_response.get('data', [])
        
        return jsonify({
            'success': True,
            'data': {
                'datasets': datasets,  # 返回真实的数据集数据
                'total_count': len(datasets),
                'message': f'成功获取 {len(datasets)} 个数据集'
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取数据集概览失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ragflow/datasets/<dataset_id>/details')
def get_dataset_details(dataset_id):
    """获取数据集详细信息 - 基于真实API"""
    try:
        ragflow_client = get_ragflow_client()
        
        # 获取数据集列表，查找指定ID的数据集
        datasets_response = ragflow_client.list_datasets()
        if not datasets_response['success']:
            return jsonify({
                'success': False,
                'error': '获取数据集信息失败',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        # 查找目标数据集
        target_dataset = None
        for dataset in datasets_response.get('data', []):
            if dataset.get('id') == dataset_id:
                target_dataset = dataset
                break
        
        if not target_dataset:
            return jsonify({
                'success': False,
                'error': '数据集不存在',
                'timestamp': datetime.now().isoformat()
            }), 404
        
        # 获取数据集文档列表
        documents_response = ragflow_client.list_documents(dataset_id)
        
        return jsonify({
            'success': True,
            'data': {
                'dataset': target_dataset,  # 真实的数据集信息
                'documents': documents_response.get('data', []) if documents_response['success'] else [],
                'documents_success': documents_response['success'],
                'documents_error': documents_response.get('error') if not documents_response['success'] else None
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取数据集详情失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ragflow/datasets', methods=['POST'])
def create_ragflow_dataset():
    """创建RAGFlow数据集 - 基于真实API"""
    try:
        data = request.get_json()
        
        name = data.get('name')
        description = data.get('description', '')
        chunk_method = data.get('chunk_method', 'naive')
        embedding_model = data.get('embedding_model', 'BAAI/bge-large-zh-v1.5@BAAI')
        
        if not name:
            return jsonify({
                'success': False,
                'error': '数据集名称不能为空',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        ragflow_client = get_ragflow_client()
        
        # 调用真实的RAGFlow API创建数据集
        result = ragflow_client.create_dataset(
            name=name,
            description=description,
            chunk_method=chunk_method,
            embedding_model=embedding_model
        )
        
        if result['success']:
            logger.info(f"数据集创建成功: {name}")
            return jsonify({
                'success': True,
                'data': result['data'],
                'dataset_id': result.get('dataset_id'),
                'message': '数据集创建成功',
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"数据集创建失败: {result['error']}")
            return jsonify({
                'success': False,
                'error': result['error'],
                'timestamp': datetime.now().isoformat()
            }), 500
             
    except Exception as e:
        logger.error(f"创建数据集失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ragflow/datasets/<dataset_id>', methods=['DELETE'])
def delete_ragflow_dataset(dataset_id):
    """删除RAGFlow数据集 - 基于真实API"""
    try:
        ragflow_client = get_ragflow_client()
        
        # 调用真实的RAGFlow API删除数据集
        result = ragflow_client.delete_dataset(dataset_id)
        
        if result['success']:
            logger.info(f"数据集删除成功: {dataset_id}")
            return jsonify({
                'success': True,
                'message': '数据集删除成功',
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"数据集删除失败: {result['error']}")
            return jsonify({
                'success': False,
                'error': result['error'],
                'timestamp': datetime.now().isoformat()
            }), 500
             
    except Exception as e:
        logger.error(f"删除数据集失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ragflow/datasets/<dataset_id>/documents', methods=['POST'])
def upload_document_to_dataset(dataset_id):
    """上传文档到数据集 - 基于真实API"""
    try:
        data = request.get_json()
        
        content = data.get('content', '').strip()
        filename = data.get('filename', f'document_{int(time.time())}.txt')
        
        if not content:
            return jsonify({
                'success': False,
                'error': '文档内容不能为空',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        ragflow_client = get_ragflow_client()
        
        # 调用真实的RAGFlow API上传文档
        result = ragflow_client.upload_text_content(
            dataset_id=dataset_id,
            content=content,
            filename=filename
        )
        
        if result['success']:
            logger.info(f"文档上传成功: {filename} 到数据集 {dataset_id}")
            return jsonify({
                'success': True,
                'data': result.get('data', {}),
                'document_id': result.get('document_id'),
                'message': '文档上传成功',
                'timestamp': datetime.now().isoformat()
            })
        else:
            error_msg = result.get('error', '未知错误')
            logger.error(f"上传文档失败: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }), 500
             
    except Exception as e:
        logger.error(f"上传文档失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ragflow/chat_assistants', methods=['GET'])
def get_ragflow_chat_assistants():
    """获取RAGFlow聊天助手列表 - 基于真实API"""
    try:
        ragflow_client = get_ragflow_client()
        
        # 调用真实的RAGFlow API获取聊天助手
        result = ragflow_client.list_chat_assistants()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data'],  # 返回真实的聊天助手数据
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'timestamp': datetime.now().isoformat()
            }), 500
             
    except Exception as e:
        logger.error(f"获取聊天助手列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ragflow/chat_assistants', methods=['POST'])
def create_ragflow_chat_assistant():
    """创建RAGFlow聊天助手 - 基于真实API"""
    try:
        data = request.get_json()
        
        name = data.get('name')
        dataset_ids = data.get('dataset_ids', [])
        description = data.get('description', '')
        
        if not name:
            return jsonify({
                'success': False,
                'error': '聊天助手名称不能为空',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        if not dataset_ids:
            return jsonify({
                'success': False,
                'error': '至少需要关联一个数据集',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        ragflow_client = get_ragflow_client()
        
        # 调用真实的RAGFlow API创建聊天助手
        result = ragflow_client.create_chat_assistant(name, dataset_ids, description)
        
        if result['success']:
            logger.info(f"聊天助手创建成功: {name}")
            return jsonify({
                'success': True,
                'data': result['data'],
                'chat_id': result.get('chat_id'),
                'message': '聊天助手创建成功',
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"聊天助手创建失败: {result['error']}")
            return jsonify({
                'success': False,
                'error': result['error'],
                'timestamp': datetime.now().isoformat()
            }), 500
             
    except Exception as e:
        logger.error(f"创建聊天助手失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ragflow/chat', methods=['POST'])
def ragflow_chat():
    """RAGFlow聊天接口 - 基于真实API"""
    try:
        data = request.get_json()
        
        chat_id = data.get('chat_id')
        question = data.get('question', '').strip()
        
        if not chat_id:
            return jsonify({
                'success': False,
                'error': '聊天助手ID不能为空',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        if not question:
            return jsonify({
                'success': False,
                'error': '问题不能为空',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        ragflow_client = get_ragflow_client()
        
        # 调用真实的RAGFlow API进行聊天
        result = ragflow_client.simple_chat(chat_id, question)
        
        if result['success']:
            logger.info(f"RAGFlow聊天成功: {question[:50]}...")
            return jsonify({
                'success': True,
                'question': result['question'],
                'answer': result['answer'],
                'usage': result.get('usage', {}),
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"RAGFlow聊天失败: {result['error']}")
            return jsonify({
                'success': False,
                'error': result['error'],
                'timestamp': datetime.now().isoformat()
            }), 500
             
    except Exception as e:
        logger.error(f"RAGFlow聊天失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ragflow/set_api_key', methods=['POST'])
def set_ragflow_key():
    """设置RAGFlow API密钥"""
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API密钥不能为空',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # 设置API密钥
        set_ragflow_api_key(api_key)
        
        # 测试连接
        ragflow_client = get_ragflow_client()
        health = ragflow_client.health_check()
        
        if health['success']:
            logger.info("RAGFlow API密钥设置并测试成功")
            return jsonify({
                'success': True,
                'message': 'RAGFlow API密钥设置成功',
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"RAGFlow API密钥测试失败: {health['error']}")
            return jsonify({
                'success': False,
                'error': f'API密钥测试失败: {health["error"]}',
                'timestamp': datetime.now().isoformat()
            }), 400
             
    except Exception as e:
        logger.error(f"设置RAGFlow API密钥失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ragflow/datasets/<dataset_id>/documents/<document_id>/parse_status')
def get_document_parse_status(dataset_id, document_id):
    """获取文档解析状态 - 基于真实API"""
    try:
        ragflow_client = get_ragflow_client()
        
        # 调用真实的RAGFlow API获取文档解析状态
        result = ragflow_client.get_document_parse_status(dataset_id, document_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result['data'],
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'timestamp': datetime.now().isoformat()
            }), 500
             
    except Exception as e:
        logger.error(f"获取文档解析状态失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/ragflow/datasets/<dataset_id>/documents/parse', methods=['POST'])
def start_document_parsing(dataset_id):
    """手动开始文档解析 - 基于真实API"""
    try:
        data = request.get_json()
        document_ids = data.get('document_ids', [])
        
        if not document_ids:
            return jsonify({
                'success': False,
                'error': '文档ID列表不能为空',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        ragflow_client = get_ragflow_client()
        
        # 调用真实的RAGFlow API开始解析
        result = ragflow_client.parse_documents(dataset_id, document_ids)
        
        if result['success']:
            logger.info(f"文档解析启动成功: 数据集 {dataset_id}, 文档数量 {len(document_ids)}")
            return jsonify({
                'success': True,
                'data': result.get('data', {}),
                'message': result.get('message', '解析启动成功'),
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.error(f"文档解析启动失败: {result['error']}")
            return jsonify({
                'success': False,
                'error': result['error'],
                'timestamp': datetime.now().isoformat()
            }), 500
             
    except Exception as e:
        logger.error(f"启动文档解析失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ==================== 主程序入口 ====================

if __name__ == '__main__':
    # 创建必要的目录
    template_dir = Path(__file__).parent / 'templates'
    static_dir = Path(__file__).parent / 'static'
    template_dir.mkdir(exist_ok=True)
    static_dir.mkdir(exist_ok=True)
    
    # 初始化系统
    logger.info("🚀 正在启动Flask应用...")
    logger.info("📋 开始系统组件初始化...")
    
    init_success = init_systems()
    
    if init_success:
        logger.info("✅ 系统初始化成功 - 所有组件已就绪")
        logger.info("🔥 InterVL API客户端已连接并可用")
        logger.info("🔗 RAGFlow API客户端已就绪，可以进行智能问答")
    else:
        logger.warning("⚠️  系统初始化失败，部分功能可能不可用")
        logger.warning("💡 建议：启动后点击'初始化系统'按钮重新初始化")
    
    # 启动应用
    logger.info("🌐 启动Flask Web服务器...")
    logger.info("📱 应用访问地址: http://localhost:5000")
    
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False  # 避免重载时的问题
    ) 