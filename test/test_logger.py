import pytest
from fastapi.testclient import TestClient
# from logger_service.main import app
from logger_service.main import get_logger, log_info
from payment_service.main import app
import os
import uuid
import logging

client = TestClient(app)

def test_logger_creation():
    """Test that logger is created correctly"""
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"

def test_log_info(tmpdir):
    """Test that log_info writes to file"""
    # Temporarily modify the log directory for testing
    import logger_service.main
    original_log_dir = logger_service.main.LOG_DIR
    logger_service.main.LOG_DIR = str(tmpdir)
    
    # Reconfigure the log handler
    log_file = os.path.join(str(tmpdir), "test.log")
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter('%(message)s')  # Simplify the format for testing
    handler.setFormatter(formatter)
    
    logger = get_logger("test_logger")
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    logger.addHandler(handler)
    
    # Write to the log
    test_message = "This is a test log message"
    log_info(test_message, "test_logger")
    
    # Check the log file
    handler.flush()
    with open(log_file, "r") as f:
        content = f.read()
    
    assert test_message in content
    
    # Restore the original path
    logger_service.main.LOG_DIR = original_log_dir
