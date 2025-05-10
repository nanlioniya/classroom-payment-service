# email_service/main.py
from fastapi import FastAPI, HTTPException, Request
import smtplib
import os
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from common_utils.logger.client import LoggerClient
from jinja2 import Environment, FileSystemLoader, select_autoescape
import pathlib
from common_utils.logger.client import LoggerClient

# Set up template directory
TEMPLATE_DIR = pathlib.Path(__file__).parent / "templates"
TEMPLATE_DIR.mkdir(exist_ok=True)

# Initialize Jinja2 environment
template_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)

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
    
    def send_email(self, to_emails, subject, html_content, text_content=None, from_email=None, cc=None, bcc=None):
        if not to_emails:
            logger.error("No recipients specified")
            return False
            
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email or self.config.default_sender
        msg["To"] = ", ".join(to_emails) if isinstance(to_emails, list) else to_emails
        
        # Add CC and BCC
        if cc:
            msg["Cc"] = ", ".join(cc) if isinstance(cc, list) else cc
        if bcc:
            msg["Bcc"] = ", ".join(bcc) if isinstance(bcc, list) else bcc
        
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
            
            # Get all recipients (including CC and BCC)
            all_recipients = to_emails.copy() if isinstance(to_emails, list) else [to_emails]
            if cc:
                all_recipients.extend(cc if isinstance(cc, list) else [cc])
            if bcc:
                all_recipients.extend(bcc if isinstance(bcc, list) else [bcc])
            
            server.sendmail(msg["From"], all_recipients, msg.as_string())
            server.quit()
            
            logger.info(f"Email sent successfully to {to_emails}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            logger.error(traceback.format_exc())
            return False

# Initialize email sender
email_config = EmailConfig()
email_sender = EmailSender(email_config)

# Template management
class TemplateManager:
    def __init__(self):
        self.templates = {}
        self._load_default_templates()
        
    def _load_default_templates(self):
        # Load default template subjects
        self.templates = {
            "payment_created": {
                "subject": "Payment Created: {{payment_id}}"
            },
            "payment_success": {
                "subject": "Payment Successful: {{payment_id}}"
            },
            "payment_failed": {
                "subject": "Payment Failed: {{payment_id}}"
            },
            "application_created": {
                "subject": "Application Created: {{application_id}}"
            },
            "application_approved": {
                "subject": "Application Approved: {{application_id}}"
            },
            "application_rejected": {
                "subject": "Application Rejected: {{application_id}}"
            },
            "application_deleted": {
                "subject": "Application Deleted: {{application_id}}"
            }
        }
        
        # Ensure template files exist
        self._create_default_templates()
        
    def _create_default_templates(self):
        # Create default template files
        templates_to_create = {
            "payment_created": {
                "html": """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #f8f9fa; padding: 10px; text-align: center; }
                        .content { padding: 20px; }
                        .footer { font-size: 12px; color: #6c757d; text-align: center; margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Payment Created</h2>
                        </div>
                        <div class="content">
                            <p>Dear Customer,</p>
                            <p>A payment has been created for your service.</p>
                            <p><strong>Payment ID:</strong> {{payment_id}}</p>
                            <p><strong>Service:</strong> {{service_name}}</p>
                            <p><strong>Amount:</strong> ${{amount}}</p>
                            {% if due_date %}
                            <p><strong>Due Date:</strong> {{due_date}}</p>
                            {% endif %}
                            <p>Please complete this payment at your earliest convenience.</p>
                            <p>Thank you for using our services!</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                "text": """
                Payment Created
                
                Dear Customer,
                
                A payment has been created for your service.
                
                Payment ID: {{payment_id}}
                Service: {{service_name}}
                Amount: ${{amount}}
                {% if due_date %}Due Date: {{due_date}}{% endif %}
                
                Please complete this payment at your earliest convenience.
                
                Thank you for using our services!
                
                This is an automated message. Please do not reply to this email.
                """
            },
            "payment_success": {
                "html": """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #d4edda; padding: 10px; text-align: center; }
                        .content { padding: 20px; }
                        .footer { font-size: 12px; color: #6c757d; text-align: center; margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Payment Successful</h2>
                        </div>
                        <div class="content">
                            <p>Dear Customer,</p>
                            <p>We're pleased to confirm that your payment has been successfully processed.</p>
                            <p><strong>Payment ID:</strong> {{payment_id}}</p>
                            <p><strong>Service:</strong> {{service_name}}</p>
                            <p><strong>Amount:</strong> ${{amount}}</p>
                            {% if transaction_id %}
                            <p><strong>Transaction ID:</strong> {{transaction_id}}</p>
                            {% endif %}
                            <p>Thank you for your payment!</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                "text": """
                Payment Successful
                
                Dear Customer,
                
                We're pleased to confirm that your payment has been successfully processed.
                
                Payment ID: {{payment_id}}
                Service: {{service_name}}
                Amount: ${{amount}}
                {% if transaction_id %}Transaction ID: {{transaction_id}}{% endif %}
                
                Thank you for your payment!
                
                This is an automated message. Please do not reply to this email.
                """
            },
            "payment_failed": {
                "html": """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #f8d7da; padding: 10px; text-align: center; }
                        .content { padding: 20px; }
                        .footer { font-size: 12px; color: #6c757d; text-align: center; margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Payment Failed</h2>
                        </div>
                        <div class="content">
                            <p>Dear Customer,</p>
                            <p>We regret to inform you that your payment could not be processed successfully.</p>
                            <p><strong>Payment ID:</strong> {{payment_id}}</p>
                            <p><strong>Service:</strong> {{service_name}}</p>
                            <p><strong>Amount:</strong> ${{amount}}</p>
                            <p><strong>Reason:</strong> {{reason}}</p>
                            <p>Please try again or contact our support team for assistance.</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                "text": """
                Payment Failed
                
                Dear Customer,
                
                We regret to inform you that your payment could not be processed successfully.
                
                Payment ID: {{payment_id}}
                Service: {{service_name}}
                Amount: ${{amount}}
                Reason: {{reason}}
                
                Please try again or contact our support team for assistance.
                
                This is an automated message. Please do not reply to this email.
                """
            },
            "application_created": {
                "html": """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #f8f9fa; padding: 10px; text-align: center; }
                        .content { padding: 20px; }
                        .footer { font-size: 12px; color: #6c757d; text-align: center; margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Application Created</h2>
                        </div>
                        <div class="content">
                            <p>Dear Customer,</p>
                            <p>Your application has been successfully created and is now under review.</p>
                            <p><strong>Application ID:</strong> {{application_id}}</p>
                            <p><strong>Service:</strong> {{service_name}}</p>
                            <p><strong>Amount:</strong> ${{amount}}</p>
                            <p>We will notify you once your application has been processed.</p>
                            <p>Thank you for your patience!</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                "text": """
                Application Created
                
                Dear Customer,
                
                Your application has been successfully created and is now under review.
                
                Application ID: {{application_id}}
                Service: {{service_name}}
                Amount: ${{amount}}
                
                We will notify you once your application has been processed.
                
                Thank you for your patience!
                
                This is an automated message. Please do not reply to this email.
                """
            },
            "application_approved": {
                "html": """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #d4edda; padding: 10px; text-align: center; }
                        .content { padding: 20px; }
                        .footer { font-size: 12px; color: #6c757d; text-align: center; margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Application Approved</h2>
                        </div>
                        <div class="content">
                            <p>Dear Customer,</p>
                            <p>We're pleased to inform you that your application has been approved!</p>
                            <p><strong>Application ID:</strong> {{application_id}}</p>
                            <p><strong>Service:</strong> {{service_name}}</p>
                            <p><strong>Amount:</strong> ${{amount}}</p>
                            <p><strong>Payment ID:</strong> {{payment_id}}</p>
                            <p>You can now proceed with the payment using the payment ID provided.</p>
                            <p>Thank you for choosing our services!</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                "text": """
                Application Approved
                
                Dear Customer,
                
                We're pleased to inform you that your application has been approved!
                
                Application ID: {{application_id}}
                Service: {{service_name}}
                Amount: ${{amount}}
                Payment ID: {{payment_id}}
                
                You can now proceed with the payment using the payment ID provided.
                
                Thank you for choosing our services!
                
                This is an automated message. Please do not reply to this email.
                """
            },
            "application_rejected": {
                "html": """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #f8d7da; padding: 10px; text-align: center; }
                        .content { padding: 20px; }
                        .footer { font-size: 12px; color: #6c757d; text-align: center; margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Application Rejected</h2>
                        </div>
                        <div class="content">
                            <p>Dear Customer,</p>
                            <p>We regret to inform you that your application has been rejected.</p>
                            <p><strong>Application ID:</strong> {{application_id}}</p>
                            <p><strong>Service:</strong> {{service_name}}</p>
                            <p><strong>Amount:</strong> ${{amount}}</p>
                            <p><strong>Reason:</strong> {{reason}}</p>
                            <p>If you have any questions or would like to submit a new application, please contact our support team.</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                "text": """
                Application Rejected
                
                Dear Customer,
                
                We regret to inform you that your application has been rejected.
                
                Application ID: {{application_id}}
                Service: {{service_name}}
                Amount: ${{amount}}
                Reason: {{reason}}
                
                If you have any questions or would like to submit a new application, please contact our support team.
                
                This is an automated message. Please do not reply to this email.
                """
            },
            "application_deleted": {
                "html": """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #f8f9fa; padding: 10px; text-align: center; }
                        .content { padding: 20px; }
                        .footer { font-size: 12px; color: #6c757d; text-align: center; margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Application Deleted</h2>
                        </div>
                        <div class="content">
                            <p>Dear Customer,</p>
                            <p>Your application has been deleted as requested.</p>
                            <p><strong>Application ID:</strong> {{application_id}}</p>
                            <p><strong>Service:</strong> {{service_name}}</p>
                            <p><strong>Amount:</strong> ${{amount}}</p>
                            <p>If you did not request this action or have any questions, please contact our support team.</p>
                        </div>
                        <div class="footer">
                            <p>This is an automated message. Please do not reply to this email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                "text": """
                Application Deleted
                
                Dear Customer,
                
                Your application has been deleted as requested.
                
                Application ID: {{application_id}}
                Service: {{service_name}}
                Amount: ${{amount}}
                
                If you did not request this action or have any questions, please contact our support team.
                
                This is an automated message. Please do not reply to this email.
                """
            }
        }
        
        for template_id, content in templates_to_create.items():
            html_path = TEMPLATE_DIR / f"{template_id}.html"
            text_path = TEMPLATE_DIR / f"{template_id}.txt"
            
            # Create HTML template
            if not html_path.exists():
                with open(html_path, "w") as f:
                    f.write(content["html"])
                    
            # Create text template
            if not text_path.exists():
                with open(text_path, "w") as f:
                    f.write(content["text"])
    
    def get_template_subject(self, template_id: str) -> str:
        """Get the default subject for a template"""
        if template_id in self.templates and "subject" in self.templates[template_id]:
            return self.templates[template_id]["subject"]
        return "Notification"
        
    def render_template(self, template_id: str, template_data: Dict[str, Any]):
        """Render template and return HTML and text versions"""
        try:
            # Get HTML template
            html_template = template_env.get_template(f"{template_id}.html")
            html_content = html_template.render(**template_data)
            
            # Get text template
            try:
                text_template = template_env.get_template(f"{template_id}.txt")
                text_content = text_template.render(**template_data)
            except:
                # If no text template, generate a simple text version
                text_content = f"Please use an HTML-compatible email client to view this message."
            
            return html_content, text_content
        except Exception as e:
            logger.error(f"Error rendering template {template_id}: {str(e)}")
            raise Exception(f"Template rendering error: {str(e)}")

# Initialize template manager
template_manager = TemplateManager()

# API Models
class EmailRequest(BaseModel):
    to: List[str]
    subject: str
    body: str
    html_body: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    sender: Optional[str] = None
    source_service: str
    attachments: Optional[List[Dict[str, Any]]] = None

class TemplateEmailRequest(BaseModel):
    to: List[str]
    template_id: str
    template_data: Dict[str, Any]
    subject: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    sender: Optional[str] = None
    source_service: str

class ApplicationCreatedRequest(BaseModel):
    recipient: str
    application_id: str
    service_name: str
    amount: float

class ApplicationRejectedRequest(BaseModel):
    recipient: str
    application_id: str
    service_name: str
    amount: float
    reason: str

class ApplicationApprovedRequest(BaseModel):
    recipient: str
    application_id: str
    service_name: str
    amount: float
    payment_id: str

class ApplicationDeletedRequest(BaseModel):
    recipient: str
    application_id: str
    service_name: str
    amount: float

class PaymentCreatedRequest(BaseModel):
    recipient: str
    payment_id: str
    service_name: str
    amount: float
    due_date: Optional[str] = None

class PaymentSuccessRequest(BaseModel):
    recipient: str
    payment_id: str
    service_name: str
    amount: float
    transaction_id: Optional[str] = None

class PaymentFailedRequest(BaseModel):
    recipient: str
    payment_id: str
    service_name: str
    amount: float
    reason: str

# API Routes
@app.get("/")
def read_root():
    return {"status": "ok", "service": "email-service"}

@app.post("/send")
async def send_email_endpoint(request: EmailRequest):
    """Send a custom email"""
    logger.info(f"Sending custom email from {request.source_service} to {request.to}")
    
    html_body = request.html_body or request.body
    
    result = email_sender.send_email(
        to_emails=request.to,
        subject=request.subject,
        html_content=html_body,
        text_content=request.body,
        from_email=request.sender,
        cc=request.cc,
        bcc=request.bcc
    )
    
    if result:
        logger.info(f"Email sent successfully from {request.source_service} to {request.to}")
        return {"status": "success", "message": "Email sent successfully"}
    else:
        logger.error(f"Failed to send email from {request.source_service} to {request.to}")
        raise HTTPException(status_code=500, detail="Failed to send email")

@app.post("/send-template")
async def send_template_email_endpoint(request: TemplateEmailRequest):
    """Send a templated email"""
    logger.info(f"Sending template email {request.template_id} from {request.source_service} to {request.to}")
    
    try:
        # Render template
        html_content, text_content = template_manager.render_template(
            template_id=request.template_id,
            template_data=request.template_data
        )
        
        # Use subject from template or request
        subject = request.subject or template_manager.get_template_subject(request.template_id)
        # Replace variables in subject
        for key, value in request.template_data.items():
            subject = subject.replace(f"{{{{{key}}}}}", str(value))
        
        # Send email
        result = email_sender.send_email(
            to_emails=request.to,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            from_email=request.sender,
            cc=request.cc,
            bcc=request.bcc
        )
        
        if result:
            logger.info(f"Template email sent successfully from {request.source_service} to {request.to}")
            return {"status": "success", "message": "Template email sent successfully"}
        else:
            logger.error(f"Failed to send template email from {request.source_service} to {request.to}")
            raise HTTPException(status_code=500, detail="Failed to send template email")
    except Exception as e:
        logger.error(f"Error processing template email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing template: {str(e)}")