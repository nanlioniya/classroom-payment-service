from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse 
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime
import csv
import os
import logging

# app = FastAPI()

# Configure log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Configure log file name (based on date)
log_file = os.path.join(LOG_DIR, f'payment_service_{datetime.now().strftime("%Y-%m-%d")}.log')

# Configure log format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create file handler
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Create logger for payment service
payment_logger = logging.getLogger('payment_service')

def get_logger(name=None):
    """Get named logger"""
    if name:
        return logging.getLogger(name)
    return payment_logger

# Shortcut functions for logging levels
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
