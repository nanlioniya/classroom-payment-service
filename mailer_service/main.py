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
from common_utils.logger.client import LoggerClient

load_dotenv()
logger = LoggerClient("mailer-service")
app = FastAPI(title="Email Service", description="Email Sending Microservice")


# Email configuration
class EmailConfig:
    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER", "sandbox.smtp.mailtrap.io").strip("'")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 2525))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "").strip("'")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "").strip("'")
        self.default_sender = os.environ.get("DEFAULT_SENDER", "payment@example.com")
        
        logger.info(f"SMTP Configuration: {self.smtp_server}:{self.smtp_port}")

# Email sender class
class EmailSender:
    def __init__(self, config=None):
        self.config = config or EmailConfig()
    
    def send_email(self, to_emails, subject, html_content, text_content=None, from_email=None):
        if not to_emails:
            logger.error("No recipients specified")
            return False
            
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email or self.config.default_sender
        msg["To"] = ", ".join(to_emails) if isinstance(to_emails, list) else to_emails
        
        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        else:
            msg.attach(MIMEText("Please use an HTML-compatible email client to view this message.", "plain", "utf-8"))
        
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        try:
            logger.info(f"Connecting to SMTP server: {self.config.smtp_server}:{self.config.smtp_port}")
            
            if os.environ.get("TESTING") == "True":
                logger.info(f"[TEST MODE] Would send email to {to_emails} with subject: {subject}")
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
            logger.info(f"Email sent successfully to {to_emails}")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

# Create email sender instance
email_sender = EmailSender()

# API models
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

class ApplicationDeletedRequest(EmailBase):
    application_id: str
    service_name: str
    amount: float
    
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

# API endpoints
@app.post("/application/created")
async def send_application_created(request: ApplicationCreatedRequest):
    """Send email for application creation success"""
    logger.info(f"Sending application created email for application ID: {request.application_id}")
    subject = f"Application Successfully Created #{request.application_id}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #4CAF50; text-align: center;">Application Successfully Created</h1>
            <p>Dear Customer,</p>
            <p>Your payment application has been successfully created. We will process your application as soon as possible.</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Application ID:</strong> {request.application_id}</p>
                <p><strong>Service Name:</strong> {request.service_name}</p>
                <p><strong>Amount:</strong> ${request.amount:.2f}</p>
                <p><strong>Application Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p>We will review your application and notify you of the result. If you have any questions, please contact our customer service.</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">Thank you for your trust!</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Application Successfully Created #{request.application_id}
    
    Dear Customer,
    
    Your payment application has been successfully created. We will process your application as soon as possible.
    
    Application ID: {request.application_id}
    Service Name: {request.service_name}
    Amount: ${request.amount:.2f}
    Application Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    We will review your application and notify you of the result. If you have any questions, please contact our customer service.
    
    Thank you for your trust!
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        logger.info(f"Application created email sent successfully for ID: {request.application_id}")
        return {"status": "success", "message": "Application creation email sent"}
    else:
        logger.error(f"Failed to send application created email for ID: {request.application_id}")
        raise HTTPException(status_code=500, detail="Failed to send application creation email")

@app.post("/application/rejected")
async def send_application_rejected(request: ApplicationRejectedRequest):
    """Send email for application rejection"""
    logger.info(f"Sending application rejected email for application ID: {request.application_id}")
    subject = f"Application Not Approved #{request.application_id}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #F44336; text-align: center;">Application Not Approved</h1>
            <p>Dear Customer,</p>
            <p>We regret to inform you that your payment application has not been approved.</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Application ID:</strong> {request.application_id}</p>
                <p><strong>Service Name:</strong> {request.service_name}</p>
                <p><strong>Amount:</strong> ${request.amount:.2f}</p>
                <p><strong>Reason for Rejection:</strong> {request.reason}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p>If you have any questions about this decision, please contact our customer service department for more information.</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">Thank you for your understanding!</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Application Not Approved #{request.application_id}
    
    Dear Customer,
    
    We regret to inform you that your payment application has not been approved.
    
    Application ID: {request.application_id}
    Service Name: {request.service_name}
    Amount: ${request.amount:.2f}
    Reason for Rejection: {request.reason}
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    If you have any questions about this decision, please contact our customer service department for more information.
    
    Thank you for your understanding!
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        logger.info(f"Application rejected email sent successfully for ID: {request.application_id}")
        return {"status": "success", "message": "Application rejection email sent"}
    else:
        logger.error(f"Failed to send application rejected email for ID: {request.application_id}")
        raise HTTPException(status_code=500, detail="Failed to send application rejection email")

@app.post("/application/approved")
async def send_application_approved(request: ApplicationApprovedRequest):
    """Send email for application approval"""
    logger.info(f"Sending application approved email for application ID: {request.application_id}")
    subject = f"Application Approved #{request.application_id}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #4CAF50; text-align: center;">Application Approved</h1>
            <p>Dear Customer,</p>
            <p>Congratulations! Your payment application has been approved.</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Application ID:</strong> {request.application_id}</p>
                <p><strong>Service Name:</strong> {request.service_name}</p>
                <p><strong>Amount:</strong> ${request.amount:.2f}</p>
                <p><strong>Payment ID:</strong> {request.payment_id}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p>We have created a payment invoice for you. Please complete the payment as soon as possible to activate the service.</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">Thank you for your support!</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Application Approved #{request.application_id}
    
    Dear Customer,
    
    Congratulations! Your payment application has been approved.
    
    Application ID: {request.application_id}
    Service Name: {request.service_name}
    Amount: ${request.amount:.2f}
    Payment ID: {request.payment_id}
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    We have created a payment invoice for you. Please complete the payment as soon as possible to activate the service.
    
    Thank you for your support!
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        logger.info(f"Application approved email sent successfully for ID: {request.application_id}")
        return {"status": "success", "message": "Application approval email sent"}
    else:
        logger.error(f"Failed to send application approved email for ID: {request.application_id}")
        raise HTTPException(status_code=500, detail="Failed to send application approval email")

@app.post("/application/deleted")
async def send_application_deleted_email(request: ApplicationDeletedRequest):
    """Send notification email for application deletion"""
    logger.info(f"Sending application deleted email for application ID: {request.application_id}")
    application_id = request.application_id
    service_name = request.service_name
    amount = request.amount
    recipient = request.recipient
    
    subject = f"Payment Application Deleted #{application_id}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #FF9800; text-align: center;">Payment Application Deleted</h1>
            <p>Dear User,</p>
            <p>Your payment application has been deleted.</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Application ID:</strong> {application_id}</p>
                <p><strong>Service Name:</strong> {service_name}</p>
                <p><strong>Application Amount:</strong> ${amount:.2f}</p>
                <p><strong>Deletion Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p>If you did not request this deletion or have any questions, please contact our customer service department immediately.</p>
            <p style="text-align: center;">
                <a href="#" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">
                    Contact Customer Service
                </a>
            </p>
            <p style="text-align: center; margin-top: 30px; color: #777;">Thank you for your understanding!</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Payment Application Deleted #{application_id}
    
    Dear User,
    
    Your payment application has been deleted.
    
    Application ID: {application_id}
    Service Name: {service_name}
    Application Amount: ${amount:.2f}
    Deletion Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    If you did not request this deletion or have any questions, please contact our customer service department immediately.
    
    Thank you for your understanding!
    """
    
    result = email_sender.send_email(
        to_emails=recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        logger.info(f"Application deleted email sent successfully for ID: {application_id}")
        return {"status": "success", "message": "Application deletion email sent"}
    else:
        logger.error(f"Failed to send application deleted email for ID: {application_id}")
        raise HTTPException(status_code=500, detail="Failed to send application deletion email")


@app.post("/payment/created")
async def send_payment_created(request: PaymentCreatedRequest):
    """Send email for payment invoice creation (payment reminder)"""
    logger.info(f"Sending payment created email for payment ID: {request.payment_id}")
    subject = f"Payment Invoice Created #{request.payment_id}"
    
    due_date_info = f"<p><strong>Due Date:</strong> {request.due_date}</p>" if request.due_date else ""
    due_date_text = f"Due Date: {request.due_date}\n" if request.due_date else ""
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #2196F3; text-align: center;">Payment Reminder</h1>
            <p>Dear Customer,</p>
            <p>Your payment invoice has been created. Please complete the payment as soon as possible.</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Payment ID:</strong> {request.payment_id}</p>
                <p><strong>Service Name:</strong> {request.service_name}</p>
                <p><strong>Amount:</strong> ${request.amount:.2f}</p>
                {due_date_info}
                <p><strong>Creation Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p style="text-align: center;">
                <a href="#" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">
                    Pay Now
                </a>
            </p>
            <p>Please complete the payment before the due date to ensure your service can be activated smoothly.</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">Thank you for your cooperation!</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Payment Reminder #{request.payment_id}
    
    Dear Customer,
    
    Your payment invoice has been created. Please complete the payment as soon as possible.
    
    Payment ID: {request.payment_id}
    Service Name: {request.service_name}
    Amount: ${request.amount:.2f}
    {due_date_text}
    Creation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    Please complete the payment before the due date to ensure your service can be activated smoothly.
    
    Thank you for your cooperation!
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        logger.info(f"Payment created email sent successfully for ID: {request.payment_id}")
        return {"status": "success", "message": "Payment creation email sent"}
    else:
        logger.error(f"Failed to send payment created email for ID: {request.payment_id}")
        raise HTTPException(status_code=500, detail="Failed to send payment creation email")

@app.post("/payment/success")
async def send_payment_success(request: PaymentSuccessRequest):
    """Send email for successful payment"""
    logger.info(f"Sending payment success email for payment ID: {request.payment_id}")
    subject = f"Payment Confirmation #{request.payment_id}"
    
    transaction_info = f"<p><strong>Transaction ID:</strong> {request.transaction_id}</p>" if request.transaction_id else ""
    transaction_text = f"Transaction ID: {request.transaction_id}\n" if request.transaction_id else ""
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #4CAF50; text-align: center;">Payment Successful</h1>
            <p>Dear Customer,</p>
            <p>Your payment has been successfully processed. Thank you for your payment!</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Payment ID:</strong> {request.payment_id}</p>
                <p><strong>Service Name:</strong> {request.service_name}</p>
                <p><strong>Amount:</strong> ${request.amount:.2f}</p>
                {transaction_info}
                <p><strong>Payment Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p>Your service is now activated. If you have any questions, please contact our customer service.</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">Thank you for your support!</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Payment Confirmation #{request.payment_id}
    
    Dear Customer,
    
    Your payment has been successfully processed. Thank you for your payment!
    
    Payment ID: {request.payment_id}
    Service Name: {request.service_name}
    Amount: ${request.amount:.2f}
    {transaction_text}
    Payment Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    Your service is now activated. If you have any questions, please contact our customer service.
    
    Thank you for your support!
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        logger.info(f"Payment success email sent successfully for ID: {request.payment_id}")
        return {"status": "success", "message": "Payment success email sent"}
    else:
        logger.error(f"Failed to send payment success email for ID: {request.payment_id}")
        raise HTTPException(status_code=500, detail="Failed to send payment success email")

@app.post("/payment/failed")
async def send_payment_failed(request: PaymentFailedRequest):
    """Send email for failed payment"""
    logger.info(f"Sending payment failed email for payment ID: {request.payment_id}")
    subject = f"Payment Processing Failed #{request.payment_id}"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h1 style="color: #F44336; text-align: center;">Payment Failed</h1>
            <p>Dear Customer,</p>
            <p>We regret to inform you that your payment processing has failed.</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Payment ID:</strong> {request.payment_id}</p>
                <p><strong>Service Name:</strong> {request.service_name}</p>
                <p><strong>Amount:</strong> ${request.amount:.2f}</p>
                <p><strong>Failure Reason:</strong> {request.reason}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <p style="text-align: center;">
                <a href="#" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">
                    Try Payment Again
                </a>
            </p>
            <p>If you need assistance, please contact our customer service department.</p>
            <p style="text-align: center; margin-top: 30px; color: #777;">Thank you for your understanding!</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Payment Processing Failed #{request.payment_id}
    
    Dear Customer,
    
    We regret to inform you that your payment processing has failed.
    
    Payment ID: {request.payment_id}
    Service Name: {request.service_name}
    Amount: ${request.amount:.2f}
    Failure Reason: {request.reason}
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    Please try the payment again or contact our customer service department for assistance.
    
    Thank you for your understanding!
    """
    
    result = email_sender.send_email(
        to_emails=request.recipient,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    if result:
        logger.info(f"Payment failed email sent successfully for ID: {request.payment_id}")
        return {"status": "success", "message": "Payment failed email sent"}
    else:
        logger.error(f"Failed to send payment failed email for ID: {request.payment_id}")
        raise HTTPException(status_code=500, detail="Failed to send payment failed email")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)