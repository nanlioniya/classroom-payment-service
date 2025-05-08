from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse 
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import csv
import os
import requests
# from logger_service.main import log_info, log_error, log_warning, log_debug, get_logger

app = FastAPI()

EMAIL_SERVICE_URL = os.environ.get("EMAIL_SERVICE_URL", "http://localhost:8001")

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
    email: EmailStr

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
    status: str # "pending", "paid", "failed"
    created_at: datetime
    email: EmailStr

class PaymentUpdate(BaseModel):
    status: str

class MessageResponse(BaseModel):
    message: str

class PaymentApplication(BaseModel):
    user_id: str
    service_id: str
    amount: float
    reason: str
    email: EmailStr
    
class PaymentApplicationResponse(BaseModel):
    application_id: str
    status: str
    created_at: str

class PaymentProcessRequest(BaseModel):
    transaction_id: Optional[str] = None

# mock database
payment_services = {}
payments = {}
payment_applications = {}

def send_email(endpoint: str, data: Dict[str, Any]) -> bool:
    url = f"{EMAIL_SERVICE_URL}/{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    print(f"Sending email to {url}")
    print(f"Email data: {data}")
    
    try:
        # Convert data to JSON string, ensuring format matches curl command
        import json
        json_data = json.dumps(data)
        print(f"JSON data: {json_data}")
        
        # Use data parameter instead of json parameter
        response = requests.post(
            url, 
            data=json_data,  # Use data instead of json
            headers=headers, 
            timeout=30  # Increase timeout
        )
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        import traceback
        print(f"Exception: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        return False

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
    # log_info(f"Creating new payment with ID: {payment_id}")

    try:
        new_payment = Payment(
            payment_id=payment_id,
            service_id=payment.service_id,
            amount=payment.amount,
            user_id=payment.user_id,
            status="pending",
            created_at=datetime.now(),
            email=payment.email
        )
        payments[payment_id] = new_payment

        # Get service name
        service_name = "Unknown Service"
        if new_payment.service_id in payment_services:
            service_name = payment_services[new_payment.service_id].name
        
        if service_name == "Unknown Service":
            raise HTTPException(status_code=404, detail="Service not found")

        due_date = new_payment.created_at + timedelta(days=30)
        # Format due_date as string (e.g., "YYYY-MM-DD")
        due_date_str = due_date.strftime("%Y-%m-%d")

        # Build email_data conforming to PaymentCreatedRequest
        email_data = {
            "recipient": new_payment.email,
            "payment_id": str(payment_id),  # Ensure it's a string
            "service_name": service_name,
            "amount": float(new_payment.amount),  # Ensure it's a float
            "due_date": due_date_str  # Ensure it's a string
        }            
        
        success = send_email("payment/created", email_data)
        if not success:
            print("Failed to send email notification")

        return {
            "payment_id": payment_id,
            "status": "pending",
            "amount": new_payment.amount,
            "created_at": new_payment.created_at.isoformat()
        }
    except Exception as e:
        # log_error(f"Error creating payment: {str(e)}")           
        raise HTTPException(status_code=500, detail="Failed to create payment")

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

    # Get service name
    service_name = "Unknown Service"
    if payment.service_id in payment_services:
        service_name = payment_services[payment.service_id].name
    if payment.status == "paid":
        # Send payment success email
        email_data = {
            "payment_id": payment_id,
            "service_name": service_name,
            "amount": payment.amount,
            "recipient": payment.email
        }            
        
        success = send_email("payment/success", email_data)
        if not success:
            print("Failed to send email notification")
    elif payment.status == "failed":
        # Send payment failed email
        email_data = {
            "payment_id": payment_id,
            "service_name": service_name,
            "amount": payment.amount,
            "reason": "invalid card",
            "recipient": payment.email
        }            
            
        success = send_email("/payment/failed", email_data)
        if not success:
            print("Failed to send email notification")
    return payment

@app.delete("/payments/{payment_id}")
async def delete_payment(payment_id: str) -> MessageResponse:
    if payment_id not in payments:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    del payments[payment_id]
    return {"message": "Payment deleted successfully"}

@app.post("/payments/apply")
async def apply_payment(application: PaymentApplication) -> PaymentApplicationResponse:
    print(f"Received payment application: {application}")
    print(f"Available services: {list(payment_services.keys())}")
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
        "created_at": datetime.now(),
        "email": application.email
    }

    # Get service name
    service_name = "Unknown Service"
    if application.service_id in payment_services:
        service_name = payment_services[application.service_id].name
    email_data = {
        "application_id": application_id,
        "service_name": service_name,
        "amount": application.amount,
        "recipient": application.email
    }            
    
    success = send_email("application/created", email_data)
    if not success:
        print("Failed to send email notification")
    
    return PaymentApplicationResponse(
        application_id=application_id,
        status="pending",
        created_at=payment_applications[application_id]["created_at"].isoformat()
    )

@app.get("/payments/applications/{application_id}")
async def get_application_info(application_id: str) -> PaymentApplicationResponse:
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
        status="completed",
        created_at=datetime.now(),
        email=application["email"]
    )
    payments[payment_id] = new_payment

    # Get service name
    service_name = "Unknown Service"
    if new_payment.service_id in payment_services:
        service_name = payment_services[new_payment.service_id].name
    email_data = {
        "application_id": application_id,
        "service_name": service_name,
        "amount": application['amount'],
        "payment_id": payment_id,
        "recipient": application["email"]
    }            
    
    success = send_email("application/approved", email_data)
    if not success:
        print("Failed to send email notification")
    
    return {"message": "Application approved and payment created", "payment_id": payment_id}

@app.put("/payments/applications/{application_id}/reject")
async def reject_application(application_id: str, reason: str) -> MessageResponse:
    """Reject payment application"""
    if application_id not in payment_applications:
        raise HTTPException(status_code=404, detail="Application not found")
    
    application = payment_applications[application_id]
    application["status"] = "rejected"

    # Get service name
    service_name = "Unknown Service"
    if application["service_id"] in payment_services:
        service_name = payment_services[application["service_id"]].name
    email_data = {
        "application_id": application_id,
        "service_name": service_name,
        "amount": application['amount'],
        "reason": reason,
        "recipient": application["email"]
    }            
    
    success = send_email("application/rejected", email_data)
    if not success:
        print("Failed to send email notification")
    
    return {"message": "Application rejected"}

@app.delete("/payments/applications/{application_id}")
async def delete_application(application_id: str) -> MessageResponse:
    """Delete payment application"""
    if application_id not in payment_applications:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Save application info for email
    application = payment_applications[application_id]
    
    # Get service name
    service_name = "Unknown Service"
    if application["service_id"] in payment_services:
        service_name = payment_services[application["service_id"]].name
    
    # Delete application
    del payment_applications[application_id]
    
    # Send deletion notification email
    email_data = {
        "application_id": application_id,
        "service_name": service_name,
        "amount": application['amount'],
        "recipient": application["email"]
    }            
    
    success = send_email("application/deleted", email_data)
    if not success:
        print("Failed to send email notification")
    
    return {"message": "Payment application successfully deleted"}

# Download payment information endpoint - in CSV format
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
    # Configure CSV directory similar to log directory
    CSV_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'csv_exports')
    os.makedirs(CSV_DIR, exist_ok=True)
    
    # Create date-based subdirectory for better organization
    date_dir = os.path.join(CSV_DIR, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)
    
    # Create CSV file path
    file_path = os.path.join(date_dir, f"payment_{payment_id}.csv")
    
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
            payment.status,
            payment.created_at.isoformat()
        ])
    
    # Return file download response
    return FileResponse(
        path=file_path,
        filename=f"payment_{payment_id}.csv",
        media_type="text/csv"
    )
