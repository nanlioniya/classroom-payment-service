# email_service/main.py
from fastapi import FastAPI, HTTPException
import smtplib
import os
import logging
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Email Service", description="郵件發送微服務")

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("email_service.log")
    ]
)

logger = logging.getLogger("email_service")
log_info = logger.info
log_error = logger.error
log_warning = logger.warning

# Email 配置
class EmailConfig:
    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER", "sandbox.smtp.mailtrap.io").strip("'")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 2525))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "").strip("'")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "").strip("'")
        self.default_sender = os.environ.get("DEFAULT_SENDER", "payment@example.com")
        
        log_info(f"SMTP Configuration: {self.smtp_server}:{self.smtp_port}")

# Email 發送類
class EmailSender:
    def __init__(self, config=None):
        self.config = config or EmailConfig()
    
    def send_email(self, to_emails, subject, html_content, text_content=None, from_email=None):
        if not to_emails:
            log_error("No recipients specified")
            return False
            
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email or self.config.default_sender
        msg["To"] = ", ".join(to_emails) if isinstance(to_emails, list) else to_emails
        
        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        else:
            msg.attach(MIMEText("請使用支援HTML的郵件客戶端查看此郵件。", "plain", "utf-8"))
        
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        try:
            log_info(f"Connecting to SMTP server: {self.config.smtp_server}:{self.config.smtp_port}")
            
            if os.environ.get("TESTING") == "True":
                log_info(f"[TEST MODE] Would send email to {to_emails} with subject: {subject}")
                return True
                
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=30)
            server.set_debuglevel(1)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.config.smtp_username, self.config.smtp_password)
            
            server.sendmail(
                msg["From"],
                to_emails if isinstance(to_emails, list) else [to_emails],
                msg.as_string()
            )
            
            server.quit()
            log_info(f"Email sent successfully to {to_emails}")
            return True
        except Exception as e:
            log_error(f"Error sending email: {str(e)}")
            log_error(f"Traceback: {traceback.format_exc()}")
            return False

# 創建郵件發送器實例
email_sender = EmailSender()

# API 模型
class EmailBase(BaseModel):
    recipient: str
    
class ApplicationCreatedRequest(EmailBase):
    application_id: str
    service_name: str
    amount: float
    
class ApplicationRejectedRequest(EmailBase):
    application_id: str
    service_name: str
    amount: float
    reason: str
    
class ApplicationApprovedRequest(EmailBase):
    application_id: str
    service_name: str
    amount: float
    payment_id: str
    
class PaymentCreatedRequest(EmailBase):
    payment_id: str
    service_name: str
    amount: float
    due_date: Optional[str] = None
    
class PaymentSuccessRequest(EmailBase):
    payment_id: str
    service_name: str
    amount: float
    transaction_id: Optional[str] = None
    
class PaymentFailedRequest(EmailBase):
    payment_id: str
    service_name: str
    amount: float
    reason: str

# API 端點
@app.post("/application/created")
async def send_application_created(request: ApplicationCreatedRequest):
    """發送申請建立成功的郵件"""
    subject = f"申請已成功建立 #{request.application_id}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #4CAF50; text-align: center;">申請已成功建立</h1>
            <p>親愛的客戶，</p>
            <p>您的付款申請已成功建立，我們將盡快處理您的申請。</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>申請編號：</strong> {request.application_id}</p>
                <p><strong>服務名稱：</strong> {request.service_name}</p>
                <p><strong>金額：</strong> ${request.amount:.2f}</p>
                <p><strong>申請日期：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p>我們將審核您的申請並通知您結果。如有任何問題，請聯繫我們的客戶服務。</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">感謝您的信任！</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    申請已成功建立 #{request.application_id}
    
    親愛的客戶，
    
    您的付款申請已成功建立，我們將盡快處理您的申請。
    
    申請編號：{request.application_id}
    服務名稱：{request.service_name}
    金額：${request.amount:.2f}
    申請日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    我們將審核您的申請並通知您結果。如有任何問題，請聯繫我們的客戶服務。
    
    感謝您的信任！
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        return {"status": "success", "message": "申請建立郵件已發送"}
    else:
        raise HTTPException(status_code=500, detail="發送申請建立郵件失敗")

@app.post("/application/rejected")
async def send_application_rejected(request: ApplicationRejectedRequest):
    """發送申請被拒絕的郵件"""
    subject = f"申請未通過 #{request.application_id}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #F44336; text-align: center;">申請未通過</h1>
            <p>親愛的客戶，</p>
            <p>很遺憾地通知您，您的付款申請未能通過審核。</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>申請編號：</strong> {request.application_id}</p>
                <p><strong>服務名稱：</strong> {request.service_name}</p>
                <p><strong>金額：</strong> ${request.amount:.2f}</p>
                <p><strong>拒絕原因：</strong> {request.reason}</p>
                <p><strong>日期：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p>如果您對此結果有任何疑問，請聯繫我們的客戶服務部門獲取更多信息。</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">感謝您的理解！</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    申請未通過 #{request.application_id}
    
    親愛的客戶，
    
    很遺憾地通知您，您的付款申請未能通過審核。
    
    申請編號：{request.application_id}
    服務名稱：{request.service_name}
    金額：${request.amount:.2f}
    拒絕原因：{request.reason}
    日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    如果您對此結果有任何疑問，請聯繫我們的客戶服務部門獲取更多信息。
    
    感謝您的理解！
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        return {"status": "success", "message": "申請拒絕郵件已發送"}
    else:
        raise HTTPException(status_code=500, detail="發送申請拒絕郵件失敗")

@app.post("/application/approved")
async def send_application_approved(request: ApplicationApprovedRequest):
    """發送申請通過的郵件"""
    subject = f"申請已通過 #{request.application_id}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #4CAF50; text-align: center;">申請已通過</h1>
            <p>親愛的客戶，</p>
            <p>恭喜！您的付款申請已通過審核。</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>申請編號：</strong> {request.application_id}</p>
                <p><strong>服務名稱：</strong> {request.service_name}</p>
                <p><strong>金額：</strong> ${request.amount:.2f}</p>
                <p><strong>付款編號：</strong> {request.payment_id}</p>
                <p><strong>日期：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p>我們已為您建立付款單，請盡快完成付款以啟用服務。</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">感謝您的支持！</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    申請已通過 #{request.application_id}
    
    親愛的客戶，
    
    恭喜！您的付款申請已通過審核。
    
    申請編號：{request.application_id}
    服務名稱：{request.service_name}
    金額：${request.amount:.2f}
    付款編號：{request.payment_id}
    日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    我們已為您建立付款單，請盡快完成付款以啟用服務。
    
    感謝您的支持！
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        return {"status": "success", "message": "申請通過郵件已發送"}
    else:
        raise HTTPException(status_code=500, detail="發送申請通過郵件失敗")

@app.post("/payment/created")
async def send_payment_created(request: PaymentCreatedRequest):
    """發送付款單建立的郵件（提醒繳費）"""
    subject = f"付款單已建立 #{request.payment_id}"
    
    due_date_info = f"<p><strong>截止日期：</strong> {request.due_date}</p>" if request.due_date else ""
    due_date_text = f"截止日期：{request.due_date}\n" if request.due_date else ""
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #2196F3; text-align: center;">付款提醒</h1>
            <p>親愛的客戶，</p>
            <p>您的付款單已建立，請盡快完成付款。</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>付款編號：</strong> {request.payment_id}</p>
                <p><strong>服務名稱：</strong> {request.service_name}</p>
                <p><strong>金額：</strong> ${request.amount:.2f}</p>
                {due_date_info}
                <p><strong>建立日期：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p style="text-align: center;">
                <a href="#" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">
                    立即付款
                </a>
            </p>
            <p>請在截止日期前完成付款，以確保服務能夠順利啟用。</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">感謝您的合作！</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    付款提醒 #{request.payment_id}
    
    親愛的客戶，
    
    您的付款單已建立，請盡快完成付款。
    
    付款編號：{request.payment_id}
    服務名稱：{request.service_name}
    金額：${request.amount:.2f}
    {due_date_text}
    建立日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    請在截止日期前完成付款，以確保服務能夠順利啟用。
    
    感謝您的合作！
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        return {"status": "success", "message": "付款建立郵件已發送"}
    else:
        raise HTTPException(status_code=500, detail="發送付款建立郵件失敗")

@app.post("/payment/success")
async def send_payment_success(request: PaymentSuccessRequest):
    """發送付款成功的郵件"""
    subject = f"付款成功確認 #{request.payment_id}"
    
    transaction_info = f"<p><strong>交易編號：</strong> {request.transaction_id}</p>" if request.transaction_id else ""
    transaction_text = f"交易編號：{request.transaction_id}\n" if request.transaction_id else ""
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #4CAF50; text-align: center;">付款成功</h1>
            <p>親愛的客戶，</p>
            <p>您的付款已成功處理。感謝您的付款！</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>付款編號：</strong> {request.payment_id}</p>
                <p><strong>服務名稱：</strong> {request.service_name}</p>
                <p><strong>金額：</strong> ${request.amount:.2f}</p>
                {transaction_info}
                <p><strong>付款日期：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p>您的服務現已啟用，如有任何問題請聯繫我們的客戶服務。</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">感謝您的支持！</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    付款成功確認 #{request.payment_id}
    
    親愛的客戶，
    
    您的付款已成功處理。感謝您的付款！
    
    付款編號：{request.payment_id}
    服務名稱：{request.service_name}
    金額：${request.amount:.2f}
    {transaction_text}
    付款日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    您的服務現已啟用，如有任何問題請聯繫我們的客戶服務。
    
    感謝您的支持！
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        return {"status": "success", "message": "付款成功郵件已發送"}
    else:
        raise HTTPException(status_code=500, detail="發送付款成功郵件失敗")

@app.post("/payment/failed")
async def send_payment_failed(request: PaymentFailedRequest):
    """發送付款失敗的郵件"""
    subject = f"付款處理失敗 #{request.payment_id}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #F44336; text-align: center;">付款失敗</h1>
            <p>親愛的客戶，</p>
            <p>很遺憾地通知您，您的付款處理失敗。</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>付款編號：</strong> {request.payment_id}</p>
                <p><strong>服務名稱：</strong> {request.service_name}</p>
                <p><strong>金額：</strong> ${request.amount:.2f}</p>
                <p><strong>失敗原因：</strong> {request.reason}</p>
                <p><strong>日期：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p style="text-align: center;">
                <a href="#" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">
                    重新嘗試付款
                </a>
            </p>
            <p>如需協助，請聯繫我們的客戶服務部門。</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">感謝您的理解！</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    付款處理失敗 #{request.payment_id}
    
    親愛的客戶，
    
    很遺憾地通知您，您的付款處理失敗。
    
    付款編號：{request.payment_id}
    服務名稱：{request.service_name}
    金額：${request.amount:.2f}
    失敗原因：{request.reason}
    日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    請重新嘗試付款或聯繫我們的客戶服務部門獲取協助。
    
    感謝您的理解！
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        return {"status": "success", "message": "付款失敗郵件已發送"}
    else:
        raise HTTPException(status_code=500, detail="發送付款失敗郵件失敗")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
