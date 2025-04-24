# test_payment_service.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_payment_service_list():
    """測試獲取所有可用的支付方案"""
    response = client.get("/payments/services")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
def test_create_payment():
    """測試創建新支付訂單"""
    payment_data = {
        "service_id": "classroom_standard",
        "amount": 100,
        "user_id": "test_user",
        "order_id": "test_order_123"
    }
    response = client.post("/payments/create", json=payment_data)
    assert response.status_code == 200
    assert "payment_id" in response.json()
    
def test_get_payment_status():
    """測試查詢支付狀態"""
    payment_id = "test_payment_123"
    response = client.get(f"/payments/{payment_id}/status")
    assert response.status_code == 200
    assert "status" in response.json()

def test_add_new_payment_service():
    """測試添加新的支付方案"""
    new_service = {
        "service_id": "classroom_premium",
        "name": "高級教室方案",
        "description": "包含更多設備的教室",
        "base_price": 200
    }
    response = client.post("/payments/services", json=new_service)
    assert response.status_code == 200
    assert response.json()["service_id"] == new_service["service_id"]


def test_create_payment_service():
    """測試創建支付服務"""
    service_data = {
        "service_id": "TEST001",
        "name": "測試支付服務",
        "description": "這是一個測試支付服務",
        "base_price": 100.0
    }
    response = client.post("/payments/services", json=service_data)
    assert response.status_code == 200
    assert response.json()["service_id"] == "TEST001"

def test_get_payment_service():
    """測試獲取單個支付服務"""
    # 先創建一個服務
    service_data = {
        "service_id": "TEST002",
        "name": "測試支付服務2",
        "description": "這是第二個測試支付服務",
        "base_price": 200.0
    }
    client.post("/payments/services", json=service_data)
    
    # 測試獲取
    response = client.get("/payments/services/TEST002")
    assert response.status_code == 200
    assert response.json()["name"] == "測試支付服務2"

def test_update_payment_service():
    """測試更新支付服務"""
    # 先創建一個服務
    service_data = {
        "service_id": "TEST003",
        "name": "測試支付服務3",
        "description": "這是第三個測試支付服務",
        "base_price": 300.0
    }
    client.post("/payments/services", json=service_data)
    
    # 更新服務
    update_data = {
        "name": "更新後的服務3",
        "description": "這是更新後的描述",
        "base_price": 350.0
    }
    response = client.put("/payments/services/TEST003", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "更新後的服務3"
    assert response.json()["base_price"] == 350.0

def test_delete_payment_service():
    """測試刪除支付服務"""
    # 先創建一個服務
    service_data = {
        "service_id": "TEST004",
        "name": "測試支付服務4",
        "description": "這是第四個測試支付服務",
        "base_price": 400.0
    }
    client.post("/payments/services", json=service_data)
    
    # 刪除服務
    response = client.delete("/payments/services/TEST004")
    assert response.status_code == 200
    
    # 確認服務已被刪除
    response = client.get("/payments/services/TEST004")
    assert response.status_code == 404