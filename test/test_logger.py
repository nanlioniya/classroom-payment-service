import pytest
from fastapi.testclient import TestClient
# from logger_service.main import app
from logger_service.main import get_logger, log_info
from payment_service.main import app
import os
import uuid
import logging

client = TestClient(app)

def test_download_payment():
    """Test downloading payment information"""
    # Create a service and payment
    service_data = {
        "service_id": "TEST009",
        "name": "Test Payment Service 9",
        "description": "Service for payment download test",
        "base_price": 500.0
    }
    client.post("/payments/services", json=service_data)
    
    payment_data = {
        "service_id": "TEST009",
        "amount": 500.0,
        "user_id": "user303",
        "order_id": "order303"
    }
   
    create_response = client.post("/payments/create", json=payment_data)
    payment_id = create_response.json()["payment_id"]
    
    response = client.get(f"/payments/{payment_id}/download")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert f"payment_{payment_id}.csv" in response.headers["content-disposition"]
    
    content = response.content.decode("utf-8")
    assert "Payment ID" in content
    assert "TEST009" in content

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
