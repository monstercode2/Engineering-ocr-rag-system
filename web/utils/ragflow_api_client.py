# -*- coding: utf-8 -*-
"""
RAGFlow API客户端
提供与RAGFlow服务交互的完整API接口
"""

import requests
import json
import time
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging

# 尝试导入dotenv，如果没有安装则使用标准的os.environ
try:
    from dotenv import load_dotenv
    # 加载项目根目录的.env文件
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[OK] 已加载环境变量文件: {env_path}")
    else:
        print(f"[WARN] 环境变量文件不存在: {env_path}")
except ImportError:
    print("[WARN] python-dotenv未安装，将直接从系统环境变量读取")
    load_dotenv = None

logger = logging.getLogger(__name__)

class RAGFlowAPIClient:
    """RAGFlow API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:9380", api_key: str = None):
        """
        初始化RAGFlow API客户端
        
        Args:
            base_url: RAGFlow服务的基础URL
            api_key: API密钥（如果不提供，将从环境变量RAGFLOW_API_KEY读取）
        """
        self.base_url = base_url.rstrip('/')
        
        # 优先使用传入的api_key，否则从环境变量读取
        self.api_key = api_key or os.getenv('RAGFLOW_API_KEY')
        
        self.session = requests.Session()
        self.session.timeout = 300  # 5分钟超时
        
        # 设置默认请求头
        self._update_auth_headers()
        
        if self.api_key:
            logger.info(f"[OK] RAGFlow API密钥已从环境变量加载: {self.api_key[:20]}...")
        else:
            logger.warning("[WARN] RAGFlow API密钥未设置，某些功能可能不可用")
    
    def _update_auth_headers(self):
        """更新认证头"""
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json'
            })
        else:
            # 移除Authorization头
            self.session.headers.pop('Authorization', None)
    
    def set_api_key(self, api_key: str):
        """
        设置API密钥
        
        Args:
            api_key: API密钥
        """
        self.api_key = api_key
        self._update_auth_headers()
        logger.info(f"已设置RAGFlow API密钥: {api_key[:20]}...")
    
    def health_check(self) -> Dict[str, Any]:
        """检查RAGFlow服务健康状态"""
        try:
            # 尝试访问数据集列表API来检查服务状态
            response = self.session.get(f"{self.base_url}/api/v1/datasets?page=1&page_size=1")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    return {
                        'success': True,
                        'status': 'healthy',
                        'response_time': response.elapsed.total_seconds()
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('message', '服务返回错误'),
                        'status_code': response.status_code
                    }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': 'API密钥无效或未提供',
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': False,
                    'error': f'RAGFlow服务返回错误状态码: {response.status_code}',
                    'status_code': response.status_code
                }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'RAGFlow服务连接失败，请检查服务是否启动'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== 数据集管理 ====================
    
    def create_dataset(self, name: str, description: str = "", 
                      chunk_method: str = "naive", 
                      embedding_model: str = "BAAI/bge-large-zh-v1.5@BAAI",
                      permission: str = "me",
                      pagerank: int = 0,
                      parser_config: Dict[str, Any] = None,
                      **kwargs) -> Dict[str, Any]:
        """
        创建数据集
        
        Args:
            name: 数据集名称
            description: 数据集描述
            chunk_method: 分块方法 (支持的值: naive, manual, qa, table, paper, book, laws, presentation, one, resume, picture, email)
            embedding_model: 嵌入模型 (格式: model_name@model_factory)
            permission: 权限设置 (me, team)
            pagerank: 页面排名 (0-100)
            parser_config: 解析器配置
            **kwargs: 其他参数
            
        Returns:
            创建结果
        """
        
        try:
            # 根据RAGFlow官方API文档构建请求参数
            data = {
                "name": name,
                "description": description,
                "chunk_method": chunk_method,
                "embedding_model": embedding_model,
                "permission": permission,
                "pagerank": pagerank
            }
            
            # 🔧 **关键修复**: 确保parser_config永远不为None
            if parser_config is None:
                # 根据chunk_method设置默认的parser_config
                if chunk_method == "naive":
                    parser_config = {
                        "chunk_token_num": 128,
                        "delimiter": "\\n",
                        "html4excel": False,
                        "layout_recognize": "DeepDOC",
                        "raptor": {"use_raptor": False},
                        "graphrag": {"use_graphrag": False},  # 防止graphrag检查错误
                        "filename_embd_weight": 0.1
                    }
                elif chunk_method in ["qa", "manual", "paper", "book", "laws", "presentation"]:
                    parser_config = {
                        "raptor": {"use_raptor": False},
                        "graphrag": {"use_graphrag": False},  # 防止graphrag检查错误
                        "filename_embd_weight": 0.1
                    }
                elif chunk_method in ["table", "picture", "one", "email"]:
                    parser_config = {
                        "graphrag": {"use_graphrag": False},  # 防止graphrag检查错误
                        "filename_embd_weight": 0.1
                    }
                else:
                    parser_config = {
                        "raptor": {"use_raptor": False},
                        "graphrag": {"use_graphrag": False},  # 防止graphrag检查错误
                        "filename_embd_weight": 0.1
                    }
            else:
                # 🔧 确保用户提供的parser_config包含必要字段
                if "filename_embd_weight" not in parser_config or parser_config["filename_embd_weight"] is None:
                    parser_config["filename_embd_weight"] = 0.1
                    logger.info("设置默认filename_embd_weight为0.1，避免None值错误")
                
                # 🔧 确保包含raptor和graphrag配置，防止AttributeError
                if "raptor" not in parser_config:
                    parser_config["raptor"] = {"use_raptor": False}
                if "graphrag" not in parser_config:
                    parser_config["graphrag"] = {"use_graphrag": False}
                    
                logger.info("已补充缺失的raptor和graphrag配置")
            
            data["parser_config"] = parser_config
            
            logger.info(f"创建数据集请求参数: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            response = self.session.post(
                f"{self.base_url}/api/v1/datasets",
                json=data
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                logger.info(f"数据集创建成功: {result}")
                return {
                    'success': True,
                    'data': result['data'],
                    'dataset_id': result['data']['id']
                }
            else:
                logger.error(f"数据集创建失败: {result}")
                return {
                    'success': False,
                    'error': result.get('message', f'HTTP {response.status_code}')
                }
                
        except Exception as e:
            logger.error(f"创建数据集时发生异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_datasets(self, page: int = 1, page_size: int = 30) -> Dict[str, Any]:
        """
        获取数据集列表
        
        Args:
            page: 页码
            page_size: 每页数量
            
        Returns:
            数据集列表
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/datasets",
                params={
                    'page': page,
                    'page_size': page_size,
                    'orderby': 'create_time',
                    'desc': 'true'
                }
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                return {
                    'success': True,
                    'data': result['data']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', f'HTTP {response.status_code}')
                }
                
        except Exception as e:
            logger.error(f"获取数据集列表失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """
        删除数据集
        
        Args:
            dataset_id: 数据集ID
            
        Returns:
            删除结果
        """
        try:
            data = {"ids": [dataset_id]}
            
            response = self.session.delete(
                f"{self.base_url}/api/v1/datasets",
                json=data
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                return {
                    'success': True,
                    'message': '数据集删除成功'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', f'HTTP {response.status_code}')
                }
                
        except Exception as e:
            logger.error(f"删除数据集失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== 文档管理 ====================
    
    def upload_document(self, dataset_id: str, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        上传文档到数据集
        
        Args:
            dataset_id: 数据集ID
            file_path: 文件路径
            
        Returns:
            上传结果
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {
                    'success': False,
                    'error': f'文件不存在: {file_path}'
                }
            
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f, 'application/octet-stream')}
                
                response = self.session.post(
                    f"{self.base_url}/api/v1/datasets/{dataset_id}/documents",
                    files=files
                )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                return {
                    'success': True,
                    'data': result['data'],
                    'document_id': result['data'][0]['id'] if result['data'] else None
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', f'HTTP {response.status_code}')
                }
                
        except Exception as e:
            logger.error(f"上传文档失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def upload_document_content(self, dataset_id: str, content: str, filename: str) -> Dict[str, Any]:
        """
        上传文本内容作为文档
        
        Args:
            dataset_id: 数据集ID
            content: 文本内容
            filename: 文件名
            
        Returns:
            上传结果
        """
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name
            
            try:
                # 上传临时文件
                with open(temp_path, 'rb') as f:
                    files = {'file': (filename, f, 'text/plain')}
                    
                    response = self.session.post(
                        f"{self.base_url}/api/v1/datasets/{dataset_id}/documents",
                        files=files
                    )
                
                result = response.json()
                
                if response.status_code == 200 and result.get('code') == 0:
                    return {
                        'success': True,
                        'data': result['data'],
                        'document_id': result['data'][0]['id'] if result['data'] else None
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('message', f'HTTP {response.status_code}')
                    }
                    
            finally:
                # 清理临时文件
                Path(temp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"上传文档内容失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def upload_text_content(self, dataset_id: str, content: str, filename: str) -> Dict[str, Any]:
        """
        上传文本内容作为文档的别名方法
        
        Args:
            dataset_id: 数据集ID
            content: 文本内容
            filename: 文件名
            
        Returns:
            上传结果
        """
        return self.upload_document_content(dataset_id, content, filename)
    
    def list_documents(self, dataset_id: str, page: int = 1, page_size: int = 30) -> Dict[str, Any]:
        """
        获取数据集中的文档列表
        
        Args:
            dataset_id: 数据集ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            文档列表
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/datasets/{dataset_id}/documents",
                params={
                    'page': page,
                    'page_size': page_size,
                    'orderby': 'create_time',
                    'desc': 'true'
                }
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                return {
                    'success': True,
                    'data': result['data']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', f'HTTP {response.status_code}')
                }
                
        except Exception as e:
            logger.error(f"获取文档列表失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== 文档解析管理 ====================
    
    def parse_documents(self, dataset_id: str, document_ids: List[str]) -> Dict[str, Any]:
        """
        开始解析数据集中的文档
        
        Args:
            dataset_id: 数据集ID
            document_ids: 要解析的文档ID列表
            
        Returns:
            解析启动结果
        """
        try:
            data = {
                "document_ids": document_ids
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/datasets/{dataset_id}/chunks",
                json=data
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                logger.info(f"文档解析启动成功: 数据集 {dataset_id}, 文档数量 {len(document_ids)}")
                return {
                    'success': True,
                    'data': result.get('data', {}),
                    'message': f'已启动 {len(document_ids)} 个文档的解析处理'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', f'HTTP {response.status_code}')
                }
                
        except Exception as e:
            logger.error(f"启动文档解析失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def stop_parsing_documents(self, dataset_id: str, document_ids: List[str]) -> Dict[str, Any]:
        """
        停止解析数据集中的文档
        
        Args:
            dataset_id: 数据集ID
            document_ids: 要停止解析的文档ID列表
            
        Returns:
            停止解析结果
        """
        try:
            data = {
                "document_ids": document_ids
            }
            
            response = self.session.delete(
                f"{self.base_url}/api/v1/datasets/{dataset_id}/chunks",
                json=data
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                logger.info(f"文档解析停止成功: 数据集 {dataset_id}, 文档数量 {len(document_ids)}")
                return {
                    'success': True,
                    'data': result.get('data', {}),
                    'message': f'已停止 {len(document_ids)} 个文档的解析处理'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', f'HTTP {response.status_code}')
                }
                
        except Exception as e:
            logger.error(f"停止文档解析失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_document_parse_status(self, dataset_id: str, document_id: str = None) -> Dict[str, Any]:
        """
        获取文档解析状态
        
        Args:
            dataset_id: 数据集ID
            document_id: 文档ID（可选，不指定则获取所有文档状态）
            
        Returns:
            解析状态信息
        """
        try:
            params = {}
            if document_id:
                params['id'] = document_id
            
            response = self.session.get(
                f"{self.base_url}/api/v1/datasets/{dataset_id}/documents",
                params=params
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                documents = result['data'].get('docs', [])
                
                # 提取解析状态信息
                status_info = []
                for doc in documents:
                    status_info.append({
                        'id': doc.get('id'),
                        'name': doc.get('name'),
                        'run': doc.get('run'),  # "0"=未开始, "1"=运行中, "2"=已完成
                        'progress': doc.get('progress', 0),  # 0-1的进度
                        'progress_msg': doc.get('progress_msg', ''),
                        'chunk_num': doc.get('chunk_num', 0),
                        'token_num': doc.get('token_num', 0),
                        'process_begin_at': doc.get('process_begin_at'),
                        'process_duration': doc.get('process_duration', 0)
                    })
                
                return {
                    'success': True,
                    'data': status_info,
                    'total': len(status_info)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', f'HTTP {response.status_code}')
                }
                
        except Exception as e:
            logger.error(f"获取文档解析状态失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== 聊天助手管理 ====================
    
    def create_chat_assistant(self, name: str, dataset_ids: List[str], 
                            description: str = "") -> Dict[str, Any]:
        """
        创建聊天助手
        
        Args:
            name: 助手名称
            dataset_ids: 关联的数据集ID列表
            description: 助手描述
            
        Returns:
            创建结果
        """
        try:
            data = {
                "name": name,
                "description": description,
                "dataset_ids": dataset_ids,
                "llm": {
                    "model_name": "",  # 使用默认模型
                    "temperature": 0.1,
                    "top_p": 0.3,
                    "presence_penalty": 0.4,
                    "frequency_penalty": 0.7,
                    "max_tokens": 512
                },
                "prompt": {
                    "system": "你是一个智能助手，请总结知识库的内容来回答问题，请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括\"知识库中未找到您要的答案！\"这句话。回答需要考虑聊天历史。",
                    "variables": [
                        {
                            "key": "knowledge",
                            "optional": False
                        }
                    ]
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/chats",
                json=data
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                return {
                    'success': True,
                    'data': result['data'],
                    'chat_id': result['data']['id']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', f'HTTP {response.status_code}')
                }
                
        except Exception as e:
            logger.error(f"创建聊天助手失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_chat_assistants(self) -> Dict[str, Any]:
        """
        获取聊天助手列表
        
        Returns:
            聊天助手列表
        """
        try:
            response = self.session.get(f"{self.base_url}/api/v1/chats")
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                return {
                    'success': True,
                    'data': result['data']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', f'HTTP {response.status_code}')
                }
                
        except Exception as e:
            logger.error(f"获取聊天助手列表失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== 对话会话管理 ====================
    
    def create_session(self, chat_id: str, name: str = "") -> Dict[str, Any]:
        """
        创建对话会话
        
        Args:
            chat_id: 聊天助手ID
            name: 会话名称
            
        Returns:
            创建结果
        """
        try:
            data = {"name": name or f"会话_{int(time.time())}"}
            
            response = self.session.post(
                f"{self.base_url}/api/v1/chats/{chat_id}/sessions",
                json=data
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('code') == 0:
                return {
                    'success': True,
                    'data': result['data'],
                    'session_id': result['data']['id']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', f'HTTP {response.status_code}')
                }
                
        except Exception as e:
            logger.error(f"创建对话会话失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== OpenAI兼容聊天 ====================
    
    def chat_completion(self, chat_id: str, messages: List[Dict[str, str]], 
                       stream: bool = False) -> Dict[str, Any]:
        """
        OpenAI兼容的聊天补全
        
        Args:
            chat_id: 聊天助手ID
            messages: 消息历史列表，格式：[{"role": "user", "content": "问题"}]
            stream: 是否流式响应
            
        Returns:
            聊天响应
        """
        try:
            data = {
                "model": "ragflow",  # 可以是任意值
                "messages": messages,
                "stream": stream
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/chats_openai/{chat_id}/chat/completions",
                json=data,
                stream=stream
            )
            
            if stream:
                # 处理流式响应
                def stream_generator():
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data: '):
                                data_str = line[6:]  # 去掉 "data: " 前缀
                                if data_str.strip() == '[DONE]':
                                    break
                                try:
                                    yield json.loads(data_str)
                                except json.JSONDecodeError:
                                    continue
                
                return {
                    'success': True,
                    'stream': True,
                    'data': stream_generator()
                }
            else:
                # 处理非流式响应
                result = response.json()
                
                if response.status_code == 200:
                    return {
                        'success': True,
                        'stream': False,
                        'data': result
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('message', f'HTTP {response.status_code}')
                    }
                    
        except Exception as e:
            logger.error(f"聊天补全失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def simple_chat(self, chat_id: str, question: str) -> Dict[str, Any]:
        """
        简单聊天接口
        
        Args:
            chat_id: 聊天助手ID
            question: 用户问题
            
        Returns:
            聊天响应
        """
        messages = [{"role": "user", "content": question}]
        result = self.chat_completion(chat_id, messages, stream=False)
        
        if result['success'] and not result['stream']:
            # 提取回答内容
            choices = result['data'].get('choices', [])
            if choices:
                answer = choices[0].get('message', {}).get('content', '')
                return {
                    'success': True,
                    'question': question,
                    'answer': answer,
                    'usage': result['data'].get('usage', {})
                }
        
        return {
            'success': False,
            'error': result.get('error', '获取回答失败')
        }

# 创建全局实例
ragflow_client = RAGFlowAPIClient()

def get_ragflow_client() -> RAGFlowAPIClient:
    """获取RAGFlow API客户端实例"""
    return ragflow_client

def set_ragflow_api_key(api_key: str):
    """设置RAGFlow API密钥"""
    global ragflow_client
    ragflow_client.api_key = api_key
    ragflow_client.session.headers.update({
        'Authorization': f'Bearer {api_key}'
    }) 