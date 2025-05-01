from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse 
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime
import csv
import os

app = FastAPI()

# model definition
class PaymentService(BaseModel):
    service_id: str
    name: str
    description: str
    base_price: float

class PaymentServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None

class PaymentCreate(BaseModel):
    service_id: str
    amount: float
    user_id: str
    order_id: str

class PaymentStatus(BaseModel):
    payment_id: str
    status: str
    amount: float
    created_at: str

class Payment(BaseModel):
    payment_id: str
    service_id: str
    amount: float
    user_id: str
    order_id: str
    status: str
    created_at: datetime

class PaymentUpdate(BaseModel):
    status: str

class MessageResponse(BaseModel):
    message: str

class PaymentApplication(BaseModel):
    user_id: str
    service_id: str
    amount: float
    reason: str
    
class PaymentApplicationResponse(BaseModel):
    application_id: str
    status: str
    created_at: str

# mock database
payment_services = {}
payments = {}
payment_applications = {}

# payment service related nodes
@app.get("/payments/services")
async def list_payment_services() -> List[PaymentService]:
    return list(payment_services.values())

@app.get("/payments/services/{service_id}")
async def get_payment_service(service_id: str) -> PaymentService:
    if service_id not in payment_services:
        raise HTTPException(status_code=404, detail="Payment service not found")
    return payment_services[service_id]

@app.post("/payments/services")
async def add_payment_service(service: PaymentService) -> PaymentService:
    if service.service_id in payment_services:
        raise HTTPException(status_code=400, detail="Service ID already exists")
    payment_services[service.service_id] = service
    return service

@app.put("/payments/services/{service_id}") 
async def update_payment_service(service_id: str, service_update: PaymentServiceUpdate) -> PaymentService:
    if service_id not in payment_services:
        raise HTTPException(status_code=404, detail="Payment service not found")
    
    update_data = service_update.model_dump(exclude_unset=True)
    current_service = payment_services[service_id]
    for field, value in update_data.items():
        setattr(current_service, field, value)
    return current_service

@app.delete("/payments/services/{service_id}")
async def delete_payment_service(service_id: str) -> MessageResponse:
    if service_id not in payment_services:
        raise HTTPException(status_code=404, detail="Payment service not found")
    del payment_services[service_id]
    return {"message": "Payment service deleted successfully"}

# payment order related nodes
@app.post("/payments/create")
async def create_payment(payment: PaymentCreate) -> PaymentStatus:
    payment_id = str(uuid.uuid4()) # identify the payment
    new_payment = Payment(
        payment_id=payment_id,
        service_id=payment.service_id,
        amount=payment.amount,
        user_id=payment.user_id,
        order_id=payment.order_id,
        status="pending",
        created_at=datetime.now()
    )
    payments[payment_id] = new_payment
    
    return {
        "payment_id": payment_id,
        "status": "pending",
        "amount": payment.amount,
        "created_at": new_payment.created_at.isoformat()
    }

@app.get("/payments/{payment_id}/info")
async def get_payment_info(payment_id: str) -> PaymentStatus:
    if payment_id not in payments:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = payments[payment_id]
    return {
        "payment_id": payment.payment_id,
        "status": payment.status,
        "amount": payment.amount,
        "created_at": payment.created_at.isoformat()
    }

@app.put("/payments/{payment_id}")
async def update_payment(payment_id: str, payment_update: PaymentUpdate) -> Payment:
    if payment_id not in payments:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = payments[payment_id]
    payment.status = payment_update.status
    return payment

@app.delete("/payments/{payment_id}")
async def delete_payment(payment_id: str) -> MessageResponse:
    if payment_id not in payments:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    del payments[payment_id]
    return {"message": "Payment deleted successfully"}

@app.post("/payments/apply")
async def apply_payment(application: PaymentApplication) -> PaymentApplicationResponse:
    """User applies for payment"""
    application_id = str(uuid.uuid4())
    
    # Check if service exists
    if application.service_id not in payment_services:
        raise HTTPException(status_code=404, detail="Payment service not found")
    
    # Create application record
    payment_applications[application_id] = {
        "application_id": application_id,
        "user_id": application.user_id,
        "service_id": application.service_id,
        "amount": application.amount,
        "reason": application.reason,
        "status": "pending",  # Initial status is pending review
        "created_at": datetime.now()
    }
    
    return {
        "application_id": application_id,
        "status": "pending",
        "created_at": payment_applications[application_id]["created_at"].isoformat()
    }

@app.get("/payments/applications/{application_id}")
async def get_application_status(application_id: str) -> PaymentApplicationResponse:
    """Get application status"""
    if application_id not in payment_applications:
        raise HTTPException(status_code=404, detail="Application not found")
    
    application = payment_applications[application_id]
    return {
        "application_id": application_id,
        "status": application["status"],
        "created_at": application["created_at"].isoformat()
    }

@app.put("/payments/applications/{application_id}/approve")
async def approve_application(application_id: str) -> dict:
    """Approve payment application"""
    if application_id not in payment_applications:
        raise HTTPException(status_code=404, detail="Application not found")
    
    application = payment_applications[application_id]
    application["status"] = "approved"
    
    # Create corresponding payment record
    payment_id = str(uuid.uuid4())
    new_payment = Payment(
        payment_id=payment_id,
        service_id=application["service_id"],
        amount=application["amount"],
        user_id=application["user_id"],
        order_id=application_id,  # Use application ID as order ID
        status="completed",
        created_at=datetime.now()
    )
    payments[payment_id] = new_payment
    
    return {"message": "Application approved and payment created", "payment_id": payment_id}

@app.put("/payments/applications/{application_id}/reject")
async def reject_application(application_id: str) -> MessageResponse:
    """Reject payment application"""
    if application_id not in payment_applications:
        raise HTTPException(status_code=404, detail="Application not found")
    
    application = payment_applications[application_id]
    application["status"] = "rejected"
    
    return {"message": "Application rejected"}

# Modified: Download payment information endpoint - in CSV format
@app.get("/payments/{payment_id}/download")
async def download_payment(payment_id: str) -> FileResponse:
    """Download payment information in CSV format"""
    if payment_id not in payments:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = payments[payment_id]
    
    # Get service name (if exists)
    service_name = "Unknown Service"
    if payment.service_id in payment_services:
        service_name = payment_services[payment.service_id].name
    
    # Create CSV file
    file_path = f"/tmp/payment_{payment_id}.csv"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Write header row
        writer.writerow([
            "Payment ID", "Service ID", "Service Name", "Amount", 
            "User ID", "Order ID", "Status", "Created At"
        ])
        
        # Write data row
        writer.writerow([
            payment.payment_id,
            payment.service_id,
            service_name,
            payment.amount,
            payment.user_id,
            payment.order_id,
            payment.status,
            payment.created_at.isoformat()
        ])
    
    # Return file download response
    return FileResponse(
        path=file_path,
        filename=f"payment_{payment_id}.csv",
        media_type="text/csv"
    )
