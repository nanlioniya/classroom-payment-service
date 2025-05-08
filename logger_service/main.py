# logger_service/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import json
import logging
from logging.handlers import RotatingFileHandler
import uuid

app = FastAPI(title="Logger Service", description="Centralized Logging Microservice")

# 配置基本日誌系統
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

# 創建日誌目錄
os.makedirs("logs", exist_ok=True)

# 為不同服務配置不同的日誌處理器
service_loggers = {}

class LogEntry(BaseModel):
    service: str
    level: str  # "INFO", "ERROR", "WARNING", "DEBUG"
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

class LogResponse(BaseModel):
    log_id: str
    status: str
    message: str

class LogQuery(BaseModel):
    service: Optional[str] = None
    level: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0

def get_logger(service_name):
    """獲取或創建特定服務的日誌記錄器"""
    if service_name not in service_loggers:
        logger = logging.getLogger(service_name)
        logger.setLevel(logging.DEBUG)
        
        # 創建服務特定的日誌文件
        file_handler = RotatingFileHandler(
            f"logs/{service_name}.log", 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        service_loggers[service_name] = logger
    
    return service_loggers[service_name]

def log_to_file(log_entry: LogEntry):
    """將日誌寫入對應服務的日誌文件"""
    logger = get_logger(log_entry.service)
    
    log_message = log_entry.message
    if log_entry.details:
        log_message += f" - Details: {json.dumps(log_entry.details)}"
    
    if log_entry.level == "INFO":
        logger.info(log_message)
    elif log_entry.level == "ERROR":
        logger.error(log_message)
    elif log_entry.level == "WARNING":
        logger.warning(log_message)
    elif log_entry.level == "DEBUG":
        logger.debug(log_message)


@app.post("/log", response_model=LogResponse)
async def create_log(log_entry: LogEntry, background_tasks: BackgroundTasks):
    """記錄一條日誌"""
    if not log_entry.timestamp:
        log_entry.timestamp = datetime.now()
    
    log_id = str(uuid.uuid4())
    
    # 使用背景任務寫入日誌，避免阻塞API響應
    background_tasks.add_task(log_to_file, log_entry)
    
    return {
        "log_id": log_id,
        "status": "success",
        "message": f"Log entry created for service {log_entry.service}"
    }

@app.get("/logs/{service_name}")
async def get_logs(
    service_name: str,
    level: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """獲取特定服務的日誌"""
    try:
        log_file = f"logs/{service_name}.log"
        if not os.path.exists(log_file):
            return {"logs": [], "total": 0}
        
        # 讀取並解析日誌文件
        logs = []
        with open(log_file, "r") as f:
            for line in f:
                # 解析日誌行
                # 這裡需要根據您的日誌格式進行調整
                logs.append(line.strip())
        
        # 應用過濾條件
        filtered_logs = logs
        if level:
            filtered_logs = [log for log in filtered_logs if level in log]
        
        # 應用分頁
        paginated_logs = filtered_logs[offset:offset+limit]
        
        return {
            "logs": paginated_logs,
            "total": len(filtered_logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving logs: {str(e)}")

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


