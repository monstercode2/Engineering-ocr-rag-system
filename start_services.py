#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工程文档智能解析与RAG问答系统 - 服务启动管理器
"""

import os
import sys
import time
import subprocess
import threading
import signal
import platform
from pathlib import Path
import requests
from typing import Dict, List, Optional

class Colors:
    """终端颜色配置"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.services: Dict[str, subprocess.Popen] = {}
        self.service_configs = {
            'intervl_api': {
                'name': 'InterVL FastAPI 服务',
                'cmd': [sys.executable, 'intervl_service.py'],
                'cwd': self.project_root / 'api',
                'port': 8000,
                'health_url': 'http://localhost:8000/health',
                'startup_delay': 5
            },
            'flask_web': {
                'name': 'Flask Web 前端',
                'cmd': [sys.executable, 'flask_app.py'],
                'cwd': self.project_root / 'web',
                'port': 5000,
                'health_url': 'http://localhost:5000/api/system/status',
                'startup_delay': 3
            }
        }
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器 - 优雅地关闭所有服务"""
        print(f"\n{Colors.WARNING}收到停止信号，正在关闭所有服务...{Colors.ENDC}")
        self.stop_all_services()
        sys.exit(0)
    
    def print_banner(self):
        """打印欢迎横幅"""
        banner = f"""
{Colors.HEADER}{Colors.BOLD}
========================================
🚀 工程文档智能解析与RAG问答系统
========================================
{Colors.ENDC}
版本: 1.0.0
平台: {platform.system()} {platform.release()}
Python: {sys.version.split()[0]}
项目路径: {self.project_root}
{Colors.OKCYAN}
💡 提示: 按 Ctrl+C 可以停止所有服务
{Colors.ENDC}
"""
        print(banner)
    
    def check_dependencies(self) -> bool:
        """检查依赖项"""
        print(f"{Colors.OKBLUE}🔍 检查项目依赖...{Colors.ENDC}")
        
        # 检查必要的目录
        required_dirs = ['api', 'web']
        missing_dirs = []
        
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)
        
        if missing_dirs:
            print(f"{Colors.FAIL}❌ 缺少必要的目录: {', '.join(missing_dirs)}{Colors.ENDC}")
            return False
        
        # 检查主要的Python文件
        required_files = {
            'api/intervl_service.py': 'InterVL服务文件',
            'web/flask_app.py': 'Flask应用文件'
        }
        
        missing_files = []
        for file_path, description in required_files.items():
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(f"{file_path} ({description})")
        
        if missing_files:
            print(f"{Colors.FAIL}❌ 缺少必要的文件:{Colors.ENDC}")
            for file_info in missing_files:
                print(f"   - {file_info}")
            return False
        
        print(f"{Colors.OKGREEN}✅ 依赖检查通过{Colors.ENDC}")
        return True
    
    def is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False
    
    def check_ports(self) -> bool:
        """检查端口占用情况"""
        print(f"{Colors.OKBLUE}🔍 检查端口占用情况...{Colors.ENDC}")
        
        occupied_ports = []
        for service_id, config in self.service_configs.items():
            port = config['port']
            if self.is_port_in_use(port):
                occupied_ports.append((port, config['name']))
        
        if occupied_ports:
            print(f"{Colors.WARNING}⚠️  以下端口已被占用:{Colors.ENDC}")
            for port, service_name in occupied_ports:
                print(f"   - 端口 {port}: {service_name}")
            
            response = input(f"\n{Colors.WARNING}是否继续启动？(y/N): {Colors.ENDC}")
            if response.lower() != 'y':
                return False
        
        print(f"{Colors.OKGREEN}✅ 端口检查完成{Colors.ENDC}")
        return True
    
    def start_service(self, service_id: str) -> bool:
        """启动单个服务"""
        config = self.service_configs[service_id]
        
        print(f"{Colors.OKBLUE}🚀 启动 {config['name']}...{Colors.ENDC}")
        
        try:
            # 创建子进程
            process = subprocess.Popen(
                config['cmd'],
                cwd=config['cwd'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            self.services[service_id] = process
            
            # 等待服务启动
            time.sleep(config['startup_delay'])
            
            # 检查进程是否还在运行
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"{Colors.FAIL}❌ {config['name']} 启动失败{Colors.ENDC}")
                print(f"错误信息: {stderr}")
                return False
            
            print(f"{Colors.OKGREEN}✅ {config['name']} 启动成功 (PID: {process.pid}){Colors.ENDC}")
            return True
            
        except Exception as e:
            print(f"{Colors.FAIL}❌ 启动 {config['name']} 时发生错误: {e}{Colors.ENDC}")
            return False
    
    def check_service_health(self, service_id: str, max_retries: int = 10) -> bool:
        """检查服务健康状态"""
        config = self.service_configs[service_id]
        health_url = config.get('health_url')
        
        if not health_url:
            return True  # 如果没有健康检查URL，假设服务正常
        
        print(f"{Colors.OKBLUE}🔍 检查 {config['name']} 健康状态...{Colors.ENDC}")
        
        for attempt in range(max_retries):
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    print(f"{Colors.OKGREEN}✅ {config['name']} 健康检查通过{Colors.ENDC}")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            if attempt < max_retries - 1:
                print(f"   尝试 {attempt + 1}/{max_retries}...")
                time.sleep(2)
        
        print(f"{Colors.WARNING}⚠️  {config['name']} 健康检查失败，但服务可能仍在启动中{Colors.ENDC}")
        return False
    
    def start_all_services(self) -> bool:
        """启动所有服务"""
        print(f"\n{Colors.HEADER}🚀 开始启动服务...{Colors.ENDC}")
        
        # 按顺序启动服务
        service_order = ['intervl_api', 'flask_web']
        
        for service_id in service_order:
            if not self.start_service(service_id):
                print(f"{Colors.FAIL}❌ 启动失败，停止后续服务启动{Colors.ENDC}")
                return False
            
            # 等待一下再启动下一个服务
            time.sleep(2)
        
        print(f"\n{Colors.OKGREEN}🎉 所有服务启动完成！{Colors.ENDC}")
        return True
    
    def monitor_services(self):
        """监控服务状态"""
        print(f"\n{Colors.OKCYAN}📊 服务状态监控 (每30秒检查一次){Colors.ENDC}")
        
        while True:
            try:
                time.sleep(30)
                
                print(f"\n{Colors.OKBLUE}📊 检查服务状态...{Colors.ENDC}")
                
                for service_id, process in self.services.items():
                    config = self.service_configs[service_id]
                    
                    if process.poll() is not None:
                        print(f"{Colors.FAIL}❌ {config['name']} 已停止 (PID: {process.pid}){Colors.ENDC}")
                    else:
                        print(f"{Colors.OKGREEN}✅ {config['name']} 运行正常 (PID: {process.pid}){Colors.ENDC}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"{Colors.WARNING}⚠️  监控过程中发生错误: {e}{Colors.ENDC}")
    
    def stop_service(self, service_id: str):
        """停止单个服务"""
        if service_id in self.services:
            process = self.services[service_id]
            config = self.service_configs[service_id]
            
            print(f"{Colors.WARNING}🛑 停止 {config['name']}...{Colors.ENDC}")
            
            try:
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print(f"{Colors.WARNING}   强制终止 {config['name']}...{Colors.ENDC}")
                process.kill()
                process.wait()
            
            del self.services[service_id]
            print(f"{Colors.OKGREEN}✅ {config['name']} 已停止{Colors.ENDC}")
    
    def stop_all_services(self):
        """停止所有服务"""
        if not self.services:
            return
        
        print(f"\n{Colors.WARNING}🛑 正在停止所有服务...{Colors.ENDC}")
        
        # 逆序停止服务
        service_ids = list(self.services.keys())
        for service_id in reversed(service_ids):
            self.stop_service(service_id)
        
        print(f"{Colors.OKGREEN}✅ 所有服务已停止{Colors.ENDC}")
    
    def print_service_urls(self):
        """打印服务访问地址"""
        urls = f"""
{Colors.HEADER}{Colors.BOLD}
📡 服务访问地址
{Colors.ENDC}{Colors.OKCYAN}
🌐 Web界面:      http://localhost:5000
🔧 InterVL API:  http://localhost:8000
📚 API文档:      http://localhost:8000/docs
💚 健康检查:     http://localhost:8000/health
{Colors.ENDC}
"""
        print(urls)
    
    def run(self):
        """运行服务管理器"""
        try:
            # 打印横幅
            self.print_banner()
            
            # 检查依赖
            if not self.check_dependencies():
                sys.exit(1)
            
            # 检查端口
            if not self.check_ports():
                sys.exit(1)
            
            # 启动服务
            if not self.start_all_services():
                self.stop_all_services()
                sys.exit(1)
            
            # 健康检查
            print(f"\n{Colors.OKBLUE}🔍 执行健康检查...{Colors.ENDC}")
            for service_id in self.services.keys():
                self.check_service_health(service_id)
            
            # 打印访问地址
            self.print_service_urls()
            
            # 开始监控
            self.monitor_services()
            
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}收到中断信号...{Colors.ENDC}")
        except Exception as e:
            print(f"\n{Colors.FAIL}发生错误: {e}{Colors.ENDC}")
        finally:
            self.stop_all_services()

def main():
    """主函数"""
    try:
        manager = ServiceManager()
        manager.run()
    except Exception as e:
        print(f"{Colors.FAIL}启动失败: {e}{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main() 