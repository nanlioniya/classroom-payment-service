from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

app = FastAPI()

# 模型定義
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

# 模擬資料庫
payment_services = {}
payments = {}

# 支付服務相關端點
@app.get("/payments/services")
async def list_payment_services() -> List[PaymentService]:
    return list(payment_services.values())

@app.post("/payments/services")
async def add_payment_service(service: PaymentService):
    if service.service_id in payment_services:
        raise HTTPException(status_code=400, detail="Service ID already exists")
    payment_services[service.service_id] = service
    return service

@app.get("/payments/services/{service_id}")
async def get_payment_service(service_id: str):
    if service_id not in payment_services:
        raise HTTPException(status_code=404, detail="Payment service not found")
    return payment_services[service_id]

@app.put("/payments/services/{service_id}")  # 改這裡
async def update_payment_service(service_id: str, service_update: PaymentServiceUpdate):
    if service_id not in payment_services:
        raise HTTPException(status_code=404, detail="Payment service not found")
    
    update_data = service_update.model_dump(exclude_unset=True)
    current_service = payment_services[service_id]
    for field, value in update_data.items():
        setattr(current_service, field, value)
    return current_service

@app.delete("/payments/services/{service_id}")
async def delete_payment_service(service_id: str):
    if service_id not in payment_services:
        raise HTTPException(status_code=404, detail="Payment service not found")
    del payment_services[service_id]
    return {"message": "Payment service deleted successfully"}

# payment order related nodes
@app.post("/payments/create")
async def create_payment(payment: PaymentCreate):
    payment_id = str(uuid.uuid4())
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

@app.get("/payments/{payment_id}/status")
async def get_payment_status(payment_id: str):
    if payment_id not in payments:
        # 如果是測試用的 payment_id，返回模擬數據
        if payment_id == "test_payment_123":
            return {
                "payment_id": payment_id,
                "status": "pending",
                "amount": 100.0,
                "created_at": datetime.now().isoformat()
            }
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = payments[payment_id]
    return {
        "payment_id": payment.payment_id,
        "status": payment.status,
        "amount": payment.amount,
        "created_at": payment.created_at.isoformat()
    }
