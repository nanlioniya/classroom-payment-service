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

# Configure basic logging system
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

# Create log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Configure different log handlers for different services
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

class LogBatchRequest(BaseModel):
    logs: List[LogEntry]

class LogBatchResponse(BaseModel):
    status: str
    count: int

class LogQuery(BaseModel):
    service: Optional[str] = None
    level: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0

def get_logger(service_name):
    """Get or create a logger for a specific service"""
    if service_name not in service_loggers:
        logger = logging.getLogger(service_name)
        logger.setLevel(logging.DEBUG)
        
        # Create service-specific log file
        file_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, f"{service_name}.log"), 
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
    """Write log to the corresponding service log file"""
    logger = get_logger(log_entry.service)
    
    log_message = log_entry.message
    if log_entry.details:
        log_message += f" - Details: {json.dumps(log_entry.details)}"
    
    if log_entry.level.upper() == "INFO":
        logger.info(log_message)
    elif log_entry.level.upper() == "ERROR":
        logger.error(log_message)
    elif log_entry.level.upper() == "WARNING":
        logger.warning(log_message)
    elif log_entry.level.upper() == "DEBUG":
        logger.debug(log_message)

def log_info(message: str, service: str):
    """Simplified logging function for recording INFO level logs"""
    logger = get_logger(service)
    logger.info(message)
    return True

@app.post("/log", response_model=dict)
async def create_log(log_entry: LogEntry, background_tasks: BackgroundTasks):
    """Record a log entry"""
    if not log_entry.timestamp:
        log_entry.timestamp = datetime.now()
    
    log_id = str(uuid.uuid4())
    
    # Use background tasks to write logs to avoid blocking API response
    background_tasks.add_task(log_to_file, log_entry)
    
    # Modified return format for compatibility with tests
    return {
        "status": "success"
    }

@app.post("/log/batch", response_model=dict)
async def create_logs_batch(request: LogBatchRequest, background_tasks: BackgroundTasks):
    """Batch record multiple log entries"""
    for log_entry in request.logs:
        if not log_entry.timestamp:
            log_entry.timestamp = datetime.now()
        background_tasks.add_task(log_to_file, log_entry)
    
    return {
        "status": "success",
        "count": len(request.logs)
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
    """Get logs for a specific service"""
    try:
        log_file = os.path.join(LOG_DIR, f"{service_name}.log")
        if not os.path.exists(log_file):
            return {"logs": [], "total": 0}
        
        # Read and parse log file
        logs = []
        with open(log_file, "r") as f:
            for line in f:
                # Parse log line
                # This needs to be adjusted according to your log format
                logs.append(line.strip())
        
        # Apply filter conditions
        filtered_logs = logs
        if level:
            filtered_logs = [log for log in filtered_logs if level in log]
        
        # Apply pagination
        paginated_logs = filtered_logs[offset:offset+limit]
        
        return {
            "logs": paginated_logs,
            "total": len(filtered_logs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving logs: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}