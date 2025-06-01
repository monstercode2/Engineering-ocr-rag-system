/**
 * 工程文档智能解析与RAG问答系统 - 通用JavaScript功能
 */

// 全局变量
let socket = null;
let notifications = [];

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * 初始化应用
 */
function initializeApp() {
    // 初始化WebSocket连接
    initializeWebSocket();
    
    // 初始化工具提示
    initializeTooltips();
    
    // 初始化通知系统
    initializeNotifications();
    
    // 添加页面加载动画
    addPageAnimations();
    
    console.log('🚀 工程文档智能解析系统已初始化');
}

/**
 * 初始化WebSocket连接
 */
function initializeWebSocket() {
    try {
        socket = io();
        
        socket.on('connect', function() {
            console.log('✓ WebSocket连接已建立');
            updateConnectionStatus(true);
        });
        
        socket.on('disconnect', function() {
            console.log('⚠ WebSocket连接已断开');
            updateConnectionStatus(false);
        });
        
        socket.on('notification', function(data) {
            showNotification(data.message, data.type || 'info');
        });
        
        socket.on('progress', function(data) {
            updateProgress(data.task_id, data.progress, data.message);
        });
        
    } catch (error) {
        console.error('WebSocket初始化失败:', error);
    }
}

/**
 * 更新连接状态
 */
function updateConnectionStatus(connected) {
    const indicators = document.querySelectorAll('.status-indicator');
    indicators.forEach(indicator => {
        if (connected) {
            indicator.classList.remove('offline');
            indicator.classList.add('online');
        } else {
            indicator.classList.remove('online');
            indicator.classList.add('offline');
        }
    });
}

/**
 * 初始化工具提示
 */
function initializeTooltips() {
    // 初始化Bootstrap工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * 初始化通知系统
 */
function initializeNotifications() {
    // 创建通知容器
    if (!document.getElementById('notificationContainer')) {
        const container = document.createElement('div');
        container.id = 'notificationContainer';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1060;
            max-width: 400px;
        `;
        document.body.appendChild(container);
    }
}

/**
 * 显示通知
 */
function showNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('notificationContainer');
    if (!container) return;
    
    const notificationId = 'notification_' + Date.now();
    const typeClasses = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'danger': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    };
    
    const typeIcons = {
        'success': 'fas fa-check-circle',
        'error': 'fas fa-exclamation-circle',
        'danger': 'fas fa-exclamation-triangle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle'
    };
    
    const alertClass = typeClasses[type] || typeClasses['info'];
    const iconClass = typeIcons[type] || typeIcons['info'];
    
    const notification = document.createElement('div');
    notification.id = notificationId;
    notification.className = `alert ${alertClass} alert-dismissible fade show notification mb-2`;
    notification.style.cssText = `
        animation: slideInRight 0.3s ease;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        border-radius: 10px;
    `;
    
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="${iconClass} me-2"></i>
            <div class="flex-grow-1">${escapeHtml(message)}</div>
            <button type="button" class="btn-close" onclick="closeNotification('${notificationId}')"></button>
        </div>
    `;
    
    container.appendChild(notification);
    
    // 自动关闭
    if (duration > 0) {
        setTimeout(() => {
            closeNotification(notificationId);
        }, duration);
    }
    
    // 记录通知
    notifications.push({
        id: notificationId,
        message: message,
        type: type,
        timestamp: new Date()
    });
}

/**
 * 关闭通知
 */
function closeNotification(notificationId) {
    const notification = document.getElementById(notificationId);
    if (notification) {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }
}

/**
 * 通用API请求函数
 */
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
        ...options
    };
    
    try {
        const response = await fetch(url, defaultOptions);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        } else {
            return await response.text();
        }
    } catch (error) {
        console.error('API请求失败:', error);
        throw error;
    }
}

/**
 * 更新进度
 */
function updateProgress(taskId, progress, message = '') {
    const progressElement = document.getElementById(`progress-${taskId}`);
    if (progressElement) {
        const progressBar = progressElement.querySelector('.progress-bar');
        const progressText = progressElement.querySelector('.progress-text');
        
        if (progressBar) {
            progressBar.style.width = progress + '%';
            progressBar.setAttribute('aria-valuenow', progress);
        }
        
        if (progressText) {
            progressText.textContent = message || `${progress}%`;
        }
    }
}

/**
 * 格式化文件大小
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 格式化时间
 */
function formatTime(date, includeSeconds = true) {
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    };
    
    if (includeSeconds) {
        options.second = '2-digit';
    }
    
    return new Date(date).toLocaleString('zh-CN', options);
}

/**
 * 格式化相对时间
 */
function formatRelativeTime(date) {
    const now = new Date();
    const diffMs = now - new Date(date);
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffSeconds < 60) {
        return '刚刚';
    } else if (diffMinutes < 60) {
        return `${diffMinutes}分钟前`;
    } else if (diffHours < 24) {
        return `${diffHours}小时前`;
    } else if (diffDays < 30) {
        return `${diffDays}天前`;
    } else {
        return formatTime(date, false);
    }
}

/**
 * HTML转义
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 防抖函数
 */
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

/**
 * 节流函数
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

/**
 * 复制到剪贴板
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('已复制到剪贴板', 'success', 2000);
        return true;
    } catch (error) {
        console.error('复制失败:', error);
        showNotification('复制失败', 'error', 2000);
        return false;
    }
}

/**
 * 下载文件
 */
function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * 添加页面动画
 */
function addPageAnimations() {
    // 为卡片添加入场动画
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in-up');
    });
    
    // 为按钮添加点击效果
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
            `;
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

/**
 * 检查网络连接
 */
function checkNetworkConnection() {
    return navigator.onLine;
}

/**
 * 获取用户代理信息
 */
function getUserAgent() {
    return {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        cookieEnabled: navigator.cookieEnabled,
        onLine: navigator.onLine
    };
}

/**
 * 本地存储操作
 */
const storage = {
    set: function(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('存储失败:', error);
            return false;
        }
    },
    
    get: function(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('读取存储失败:', error);
            return defaultValue;
        }
    },
    
    remove: function(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('删除存储失败:', error);
            return false;
        }
    },
    
    clear: function() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('清空存储失败:', error);
            return false;
        }
    }
};

/**
 * 系统诊断信息
 */
function getSystemInfo() {
    return {
        timestamp: new Date().toISOString(),
        userAgent: getUserAgent(),
        screen: {
            width: screen.width,
            height: screen.height,
            colorDepth: screen.colorDepth
        },
        viewport: {
            width: window.innerWidth,
            height: window.innerHeight
        },
        connection: checkNetworkConnection(),
        notifications: notifications.slice(-10), // 最近10条通知
        performance: {
            memory: performance.memory ? {
                used: Math.round(performance.memory.usedJSHeapSize / 1048576) + 'MB',
                total: Math.round(performance.memory.totalJSHeapSize / 1048576) + 'MB',
                limit: Math.round(performance.memory.jsHeapSizeLimit / 1048576) + 'MB'
            } : null
        }
    };
}

// 添加ripple动画CSS
const rippleCSS = `
@keyframes ripple {
    to {
        transform: scale(4);
        opacity: 0;
    }
}
`;

// 添加slideOutRight动画CSS
const slideOutCSS = `
@keyframes slideOutRight {
    from {
        opacity: 1;
        transform: translateX(0);
    }
    to {
        opacity: 0;
        transform: translateX(100px);
    }
}
`;

// 注入CSS动画
const style = document.createElement('style');
style.textContent = rippleCSS + slideOutCSS;
document.head.appendChild(style);

// 导出全局函数
window.showNotification = showNotification;
window.closeNotification = closeNotification;
window.apiRequest = apiRequest;
window.formatFileSize = formatFileSize;
window.formatTime = formatTime;
window.formatRelativeTime = formatRelativeTime;
window.copyToClipboard = copyToClipboard;
window.downloadFile = downloadFile;
window.storage = storage;
window.getSystemInfo = getSystemInfo;

console.log('📱 通用JavaScript功能已加载'); 