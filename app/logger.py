import logging
import os
from datetime import datetime

# 配置日誌目錄
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 配置日誌文件名（按日期）
log_file = os.path.join(LOG_DIR, f'payment_service_{datetime.now().strftime("%Y-%m-%d")}.log')

# 配置日誌格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 創建文件處理器
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)

# 創建控制台處理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 配置根日誌記錄器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# 創建支付服務專用日誌記錄器
payment_logger = logging.getLogger('payment_service')

def get_logger(name=None):
    """獲取命名日誌記錄器"""
    if name:
        return logging.getLogger(name)
    return payment_logger

# 日誌級別快捷函數
def log_info(message, logger_name=None):
    logger = get_logger(logger_name)
    logger.info(message)

def log_error(message, logger_name=None):
    logger = get_logger(logger_name)
    logger.error(message)

def log_warning(message, logger_name=None):
    logger = get_logger(logger_name)
    logger.warning(message)

def log_debug(message, logger_name=None):
    logger = get_logger(logger_name)
    logger.debug(message)
