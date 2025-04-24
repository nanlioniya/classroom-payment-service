# test_payment_service.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_payment_service_list():
    """Test retrieving all available payment services"""
    response = client.get("/payments/services")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_payment():
    """Test retrieving a single payment service"""
    # First create a service
    service_data = {
        "service_id": "TEST001",
        "name": "Test Payment Service 1",
        "description": "This is the second test payment service",
        "base_price": 200.0
    }
    client.post("/payments/services", json=service_data)
    
    # Test retrieving
    response = client.get("/payments/services/TEST001")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Payment Service 1"

def test_add_new_payment_service():
    """Test adding a new payment service"""
    new_service = {
        "service_id": "classroom_premium",
        "name": "Premium Classroom Plan",
        "description": "Classroom with more equipment",
        "base_price": 200
    }
    response = client.post("/payments/services", json=new_service)
    assert response.status_code == 200
    assert response.json()["service_id"] == new_service["service_id"]

def test_update_payment_service():
    """Test updating a payment service"""
    # First create a service
    service_data = {
        "service_id": "TEST002",
        "name": "Test Payment Service 2",
        "description": "This is the third test payment service",
        "base_price": 300.0
    }
    client.post("/payments/services", json=service_data)
    
    # Update the service
    update_data = {
        "name": "Updated Service 2",
        "description": "This is the updated description",
        "base_price": 350.0
    }
    response = client.put("/payments/services/TEST002", json=update_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Service 2"
    assert response.json()["base_price"] == 350.0

def test_delete_payment_service():
    """Test deleting a payment service"""
    # First create a service
    service_data = {
        "service_id": "TEST003",
        "name": "Test Payment Service 3",
        "description": "This is the third test payment service",
        "base_price": 400.0
    }
    client.post("/payments/services", json=service_data)
    
    # Delete the service
    response = client.delete("/payments/services/TEST003")
    assert response.status_code == 200
    
    # Confirm the service has been deleted
    response = client.get("/payments/services/TEST003")
    assert response.status_code == 404
    
def test_create_payment():
    """Test creating a new payment order"""
    payment_data = {
        "service_id": "classroom_standard",
        "amount": 100,
        "user_id": "test_user",
        "order_id": "test_order_123"
    }
    response = client.post("/payments/create", json=payment_data)
    assert response.status_code == 200
    assert "payment_id" in response.json()

def test_get_payment_info():
    """Test querying payment status"""
    # First create a payment order
    payment_data = {
        "service_id": "test_service",
        "amount": 150.0,
        "user_id": "test_user_456",
        "order_id": "test_order_456"
    }
    create_response = client.post("/payments/create", json=payment_data)
    assert create_response.status_code == 200
    
    # Get the payment_id from the response
    payment_id = create_response.json()["payment_id"]
    
    # Now test querying the payment status
    response = client.get(f"/payments/{payment_id}/status")
    assert response.status_code == 200
    assert response.json()["amount"] == 150.0
    assert response.json()["status"] == "pending"

def test_update_payment_status():
    """Test updating payment order status"""
    # First create a payment order
    payment_data = {
        "service_id": "test_service",
        "amount": 100,
        "user_id": "test_user",
        "order_id": "test_order"
    }
    create_response = client.post("/payments/create", json=payment_data)
    payment_id = create_response.json()["payment_id"]
    
    # Update payment status
    update_data = {
        "status": "completed"
    }
    response = client.put(f"/payments/{payment_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    # Test updating a non-existent payment order
    update_data = {
        "status": "completed"
    }
    response = client.put("/payments/non_existent_id", json=update_data)
    assert response.status_code == 404


def test_delete_payment():
    """Test deleting a payment order"""
    # First create a payment order
    payment_data = {
        "service_id": "test_service",
        "amount": 100,
        "user_id": "test_user",
        "order_id": "test_order"
    }
    create_response = client.post("/payments/create", json=payment_data)
    payment_id = create_response.json()["payment_id"]
    
    # Delete the payment order
    response = client.delete(f"/payments/{payment_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Payment deleted successfully"
    
    # Confirm the order has been deleted
    get_response = client.get(f"/payments/{payment_id}/status")
    assert get_response.status_code == 404

    # Test deleting a non-existent payment order
    response = client.delete("/payments/non_existent_id")
    assert response.status_code == 404
