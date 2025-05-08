from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse 
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import csv
import os
import requests
from common_utils.logger.client import LoggerClient

app = FastAPI()
logger = LoggerClient("payment-service")
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
    
    logger.debug(f"Sending email to {url}", {"endpoint": endpoint, "data": data})
    
    try:
        # Convert data to JSON string, ensuring format matches curl command
        import json
        json_data = json.dumps(data)
        logger.debug(f"JSON data: {json_data}", {"json_data": json_data})
        
        # Use data parameter instead of json parameter
        response = requests.post(
            url, 
            data=json_data,  # Use data instead of json
            headers=headers, 
            timeout=30  # Increase timeout
        )
        
        logger.debug(f"Email response", {
            "status_code": response.status_code,
            "content": response.text
        })
        
        return response.status_code == 200
    except Exception as e:
        import traceback
        logger.error(f"Failed to send email", {
            "error": str(e),
            "stack_trace": traceback.format_exc(),
            "endpoint": endpoint
        })
        return False

# payment service related nodes
@app.get("/payments/services")
async def list_payment_services() -> List[PaymentService]:
    logger.info("Listing all payment services", {})
    return list(payment_services.values())

@app.get("/payments/services/{service_id}")
async def get_payment_service(service_id: str) -> PaymentService:
    logger.info(f"Getting payment service details", {"service_id": service_id})
    if service_id not in payment_services:
        logger.warning(f"Payment service not found", {"service_id": service_id})
        raise HTTPException(status_code=404, detail="Payment service not found")
    logger.debug(f"Payment service found", {"service_id": service_id, "service_name": payment_services[service_id].name})
    return payment_services[service_id]

@app.post("/payments/services")
async def add_payment_service(service: PaymentService) -> PaymentService:
    logger.info(f"Adding new payment service", {"service_id": service.service_id, "name": service.name})
    if service.service_id in payment_services:
        logger.warning(f"Service ID already exists", {"service_id": service.service_id})
        raise HTTPException(status_code=400, detail="Service ID already exists")
    payment_services[service.service_id] = service
    logger.info(f"Payment service added successfully", {"service_id": service.service_id})
    return service

@app.put("/payments/services/{service_id}") 
async def update_payment_service(service_id: str, service_update: PaymentServiceUpdate) -> PaymentService:
    logger.info(f"Updating payment service", {"service_id": service_id})
    if service_id not in payment_services:
        logger.warning(f"Payment service not found", {"service_id": service_id})
        raise HTTPException(status_code=404, detail="Payment service not found")
    
    update_data = service_update.model_dump(exclude_unset=True)
    current_service = payment_services[service_id]
    for field, value in update_data.items():
        setattr(current_service, field, value)
    logger.info(f"Payment service updated successfully", {"service_id": service_id, "updated_fields": list(update_data.keys())})
    return current_service

@app.delete("/payments/services/{service_id}")
async def delete_payment_service(service_id: str) -> MessageResponse:
    logger.info(f"Deleting payment service", {"service_id": service_id})
    if service_id not in payment_services:
        raise HTTPException(status_code=404, detail="Payment service not found")
    del payment_services[service_id]
    logger.info(f"Payment service deleted successfully", {"service_id": service_id})
    return {"message": "Payment service deleted successfully"}

# payment order related nodes
@app.post("/payments/create")
async def create_payment(payment: PaymentCreate) -> PaymentStatus:
    payment_id = str(uuid.uuid4()) # identify the payment
    logger.info(f"Creating new payment", {"payment_id": payment_id, "user_id": payment.user_id})
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
            logger.warning(f"Service not found for payment", {"payment_id": payment_id, "service_id": payment.service_id})
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
            logger.warning("Failed to send email notification", {"payment_id": payment_id, "email": new_payment.email})
        # 記錄成功的支付
        logger.info(f"Payment created for user {payment.user_id}", {
            "payment_id": payment_id,
            "amount": payment.amount,
            "service_id": payment.service_id
        })

        return {
            "payment_id": payment_id,
            "status": "pending",
            "amount": new_payment.amount,
            "created_at": new_payment.created_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to create payment: {str(e)}", {
            "user_id": payment.user_id,
            "service_id": payment.service_id,
            "error": str(e)
        })      
        raise HTTPException(status_code=500, detail="Failed to create payment")

@app.get("/payments/{payment_id}/info")
async def get_payment_info(payment_id: str) -> PaymentStatus:
    logger.info(f"Getting payment info", {"payment_id": payment_id})
    if payment_id not in payments:
        logger.warning(f"Payment not found", {"payment_id": payment_id})
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
    logger.info(f"Updating payment status", {"payment_id": payment_id, "new_status": payment_update.status})
    if payment_id not in payments:
        logger.warning(f"Payment not found", {"payment_id": payment_id})
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = payments[payment_id]
    payment.status = payment_update.status

    # Get service name
    service_name = "Unknown Service"
    if payment.service_id in payment_services:
        service_name = payment_services[payment.service_id].name
    if payment.status == "paid":
        logger.info(f"Payment marked as paid", {"payment_id": payment_id})
        # Send payment success email
        email_data = {
            "payment_id": payment_id,
            "service_name": service_name,
            "amount": payment.amount,
            "recipient": payment.email
        }            
        
        success = send_email("payment/success", email_data)
        if not success:
            logger.warning("Failed to send payment success email", {"payment_id": payment_id, "email": payment.email})
    elif payment.status == "failed":
        logger.info(f"Payment marked as failed", {"payment_id": payment_id})
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
            logger.warning("Failed to send payment failure email", {"payment_id": payment_id, "email": payment.email})
    return payment

@app.delete("/payments/{payment_id}")
async def delete_payment(payment_id: str) -> MessageResponse:
    logger.info(f"Deleting payment", {"payment_id": payment_id})
    if payment_id not in payments:
        logger.warning(f"Payment not found", {"payment_id": payment_id})
        raise HTTPException(status_code=404, detail="Payment not found")
    
    del payments[payment_id]
    logger.info(f"Payment deleted successfully", {"payment_id": payment_id})
    return {"message": "Payment deleted successfully"}

@app.post("/payments/apply")
async def apply_payment(application: PaymentApplication) -> PaymentApplicationResponse:
    logger.info(f"Received payment application", {"user_id": application.user_id, "service_id": application.service_id})
    logger.debug(f"Available services", {"services": list(payment_services.keys())})
    """User applies for payment"""
    application_id = str(uuid.uuid4())
    
    # Check if service exists
    if application.service_id not in payment_services:
        logger.warning(f"Payment service not found", {"service_id": application.service_id})
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
        logger.warning("Failed to send email notification", {"application_id": application_id, "email": application.email})
    
    logger.info(f"Payment application created", {"application_id": application_id, "status": "pending"})
    return PaymentApplicationResponse(
        application_id=application_id,
        status="pending",
        created_at=payment_applications[application_id]["created_at"].isoformat()
    )

@app.get("/payments/applications/{application_id}")
async def get_application_info(application_id: str) -> PaymentApplicationResponse:
    """Get application status"""
    logger.info(f"Getting application info", {"application_id": application_id})
    if application_id not in payment_applications:
        logger.warning(f"Application not found", {"application_id": application_id})
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
    logger.info(f"Approving payment application", {"application_id": application_id})
    if application_id not in payment_applications:
        logger.warning(f"Application not found", {"application_id": application_id})
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
        logger.warning("Failed to send application approved email", {"application_id": application_id, "email": application["email"]})
    
    logger.info(f"Application approved and payment created", {"application_id": application_id, "payment_id": payment_id})
    return {"message": "Application approved and payment created", "payment_id": payment_id}

@app.put("/payments/applications/{application_id}/reject")
async def reject_application(application_id: str, reason: str) -> MessageResponse:
    """Reject payment application"""
    logger.info(f"Rejecting payment application", {"application_id": application_id, "reason": reason})
    if application_id not in payment_applications:
        logger.warning(f"Application not found", {"application_id": application_id})
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
        logger.warning("Failed to send application rejected email", {"application_id": application_id, "email": application["email"]})
    
    logger.info(f"Application rejected", {"application_id": application_id})
    return {"message": "Application rejected"}

@app.delete("/payments/applications/{application_id}")
async def delete_application(application_id: str) -> MessageResponse:
    """Delete payment application"""
    logger.info(f"Deleting payment application", {"application_id": application_id})
    if application_id not in payment_applications:
        logger.warning(f"Application not found", {"application_id": application_id})
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
        logger.warning("Failed to send application deleted email", {"application_id": application_id, "email": application["email"]})
    
    logger.info(f"Payment application successfully deleted", {"application_id": application_id})
    return {"message": "Payment application successfully deleted"}

# Download payment information endpoint - in CSV format
@app.get("/payments/{payment_id}/download")
async def download_payment(payment_id: str) -> FileResponse:
    """Download payment information in CSV format"""
    logger.info(f"Downloading payment information", {"payment_id": payment_id})
    if payment_id not in payments:
        logger.warning(f"Payment not found", {"payment_id": payment_id})
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
    
    logger.debug(f"Creating CSV file", {"file_path": file_path})
    
    try:
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Write header row
            writer.writerow([
                "Payment ID", "Service ID", "Service Name", "Amount",
                    "User ID", "Status", "Created At"
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
        
            logger.info(f"CSV file created successfully", {"payment_id": payment_id, "file_path": file_path})
            
        # Return file download response
        return FileResponse(
            path=file_path,
            filename=f"payment_{payment_id}.csv",
            media_type="text/csv"
        )
    except Exception as e:
        logger.error(f"Failed to create CSV file", {
            "payment_id": payment_id,
            "error": str(e),
            "file_path": file_path
        })
        raise HTTPException(status_code=500, detail="Failed to generate payment CSV")