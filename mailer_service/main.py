from fastapi import FastAPI, HTTPException
import smtplib
import os
import logging
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

app = FastAPI()

# Set up basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("email_service.log")
    ]
)

# Create logger
logger = logging.getLogger("email_service")

# If you have already set up logging, you can import it
try:
    from logger import log_info, log_error, log_warning
except ImportError:
    # If import fails, create simple logging functions
    log_info = logger.info
    log_error = logger.error
    log_warning = logger.warning


class EmailConfig:
    """Email configuration class"""
    def __init__(self):
        # Mailtrap configuration - corrected server address
        self.smtp_server = os.environ.get("SMTP_SERVER", "sandbox.smtp.mailtrap.io")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 2525))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.default_sender = os.environ.get("DEFAULT_SENDER", "payment@example.com")
        
        # Log configuration details (without sensitive information)
        log_info(f"SMTP Configuration: {self.smtp_server}:{self.smtp_port}")
        log_info(f"Default sender: {self.default_sender}")
        
        # If environment variables are not set, prompt the user
        if not self.smtp_username or not self.smtp_password:
            log_warning("Mailtrap credentials not set. Please set SMTP_USERNAME and SMTP_PASSWORD environment variables.")


class EmailSender:
    """Email sender class"""
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig()
    
    def send_email(self, 
                  to_emails: List[str], 
                  subject: str, 
                  html_content: str, 
                  text_content: str = None,
                  from_email: str = None) -> bool:
        """
        Send email
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_content: HTML formatted email content
            text_content: Plain text email content (optional)
            from_email: Sender email address (optional, default to the default sender in the configuration)
            
        Returns:
            bool: Whether the email was sent successfully
        """
        if not to_emails:
            log_error("No recipients specified")
            return False
            
        # Create the email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email or self.config.default_sender
        msg["To"] = ", ".join(to_emails)
        
        # Add plain text content
        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        else:
            # If no plain text content is provided, use a simple text version
            msg.attach(MIMEText("Please view this email in an HTML-enabled email client.", "plain", "utf-8"))
        
        # Add HTML content
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        
        try:
            # Connect to the Mailtrap SMTP server with detailed logging
            log_info(f"Connecting to SMTP server: {self.config.smtp_server}:{self.config.smtp_port}")
            
            # Create SMTP connection with extended timeout
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=30)
            
            # Enable debug mode
            server.set_debuglevel(1)
            
            # Identify ourselves to the server
            log_info("Sending EHLO command")
            server.ehlo()
            
            # Start TLS encryption
            log_info("Starting TLS encryption")
            server.starttls()
            
            # Re-identify ourselves over TLS connection
            log_info("Sending EHLO command after STARTTLS")
            server.ehlo()
            
            # Login with credentials
            log_info(f"Logging in with username: {self.config.smtp_username}")
            server.login(self.config.smtp_username, self.config.smtp_password)
            
            # Send the email
            log_info(f"Sending email to: {', '.join(to_emails)}")
            server.sendmail(
                msg["From"],
                to_emails,
                msg.as_string()
            )
            
            # Close the connection
            log_info("Closing SMTP connection")
            server.quit()
            
            log_info(f"Email sent successfully to {', '.join(to_emails)}")
            return True
        except Exception as e:
            log_error(f"Error sending email: {str(e)}")
            # Add more detailed error information
            log_error(f"Traceback: {traceback.format_exc()}")
            return False


class EmailTemplates:
    """Predefined email templates"""
    
    @staticmethod
    def payment_confirmation(payment_id: str, amount: float, service_name: str) -> tuple:
        """
        Payment confirmation email template
        
        Returns:
            tuple: (subject, html_content, text_content)
        """
        subject = f"Payment Confirmation #{payment_id}"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ width: 80%; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 10px; text-align: center; }}
                .content {{ padding: 20px; border: 1px solid #ddd; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Payment Confirmation</h1>
                </div>
                <div class="content">
                    <p>Dear,</p>
                    <p>We have received your payment. Here are the transaction details:</p>
                    <ul>
                        <li><strong>Payment ID:</strong> {payment_id}</li>
                        <li><strong>Amount:</strong> ${amount:.2f}</li>
                        <li><strong>Service:</strong> {service_name}</li>
                        <li><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <p>If you have any questions, please feel free to contact our customer support team.</p>
                    <p>Thank you!</p>
                </div>
                <div class="footer">
                    <p>This email is automatically generated. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Payment Confirmation #{payment_id}
        
        Dear,
        
        We have received your payment. Here are the transaction details:
        
        - Payment ID: {payment_id}
        - Amount: ${amount:.2f}
        - Service: {service_name}
        - Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        If you have any questions, please feel free to contact our customer support team.
        
        Thank you!
        
        This email is automatically generated. Please do not reply.
        """
        
        return subject, html_content, text_content
    
    @staticmethod
    def payment_failed(payment_id: str, amount: float, reason: str) -> tuple:
        """
        Payment failure email template
        
        Returns:
            tuple: (subject, html_content, text_content)
        """
        subject = f"Payment Failed Notification #{payment_id}"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ width: 80%; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f44336; color: white; padding: 10px; text-align: center; }}
                .content {{ padding: 20px; border: 1px solid #ddd; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Payment Failure Notification</h1>
                </div>
                <div class="content">
                    <p>Dear,</p>
                    <p>We are sorry to inform you that your payment transaction could not be completed. Here are the details:</p>
                    <ul>
                        <li><strong>Payment ID:</strong> {payment_id}</li>
                        <li><strong>Amount:</strong> ${amount:.2f}</li>
                        <li><strong>Failure Reason:</strong> {reason}</li>
                        <li><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                    <p>Please try again later or use an alternative payment method. If you need assistance, please contact our customer support team.</p>
                    <p>Thank you!</p>
                </div>
                <div class="footer">
                    <p>This email is automatically generated. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Payment Failure Notification #{payment_id}
        
        Dear,
        
        We are sorry to inform you that your payment transaction could not be completed. Here are the details:
        
        - Payment ID: {payment_id}
        - Amount: ${amount:.2f}
        - Failure Reason: {reason}
        - Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Please try again later or use an alternative payment method. If you need assistance, please contact our customer support team.
        
        Thank you!
        
        This email is automatically generated. Please do not reply.
        """
        
        return subject, html_content, text_content


# Create a default email sender instance for easy import and use
email_sender = EmailSender()

# Convenient function for sending payment confirmation email
def send_payment_confirmation(to_email: str, payment_id: str, amount: float, service_name: str) -> bool:
    """Send payment confirmation email"""
    subject, html, text = EmailTemplates.payment_confirmation(payment_id, amount, service_name)
    return email_sender.send_email([to_email], subject, html, text)

# Convenient function for sending payment failure email
def send_payment_failed(to_email: str, payment_id: str, amount: float, reason: str) -> bool:
    """Send payment failure email"""
    subject, html, text = EmailTemplates.payment_failed(payment_id, amount, reason)
    return email_sender.send_email([to_email], subject, html, text)


# API Models
class EmailRequest(BaseModel):
    recipient: str
    payment_id: str
    amount: float
    service_name: str = "Default Service"


class FailedEmailRequest(BaseModel):
    recipient: str
    payment_id: str
    amount: float
    reason: str


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Email Service API is running"}


@app.post("/send-confirmation/")
async def send_confirmation_email(request: EmailRequest):
    """Send payment confirmation email"""
    try:
        result = send_payment_confirmation(
            to_email=request.recipient,
            payment_id=request.payment_id,
            amount=request.amount,
            service_name=request.service_name
        )
        
        if result:
            return {"status": "success", "message": f"Confirmation email sent to {request.recipient}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send confirmation email")
    except Exception as e:
        log_error(f"Error in send-confirmation endpoint: {str(e)}")
        log_error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error sending confirmation email: {str(e)}")


@app.post("/send-failed/")
async def send_failed_email(request: FailedEmailRequest):
    """Send payment failed email"""
    try:
        result = send_payment_failed(
            to_email=request.recipient,
            payment_id=request.payment_id,
            amount=request.amount,
            reason=request.reason
        )
        
        if result:
            return {"status": "success", "message": f"Payment failed email sent to {request.recipient}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send payment failed email")
    except Exception as e:
        log_error(f"Error in send-failed endpoint: {str(e)}")
        log_error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error sending payment failed email: {str(e)}")


@app.post("/test-email/")
async def test_email(recipient: str):
    """Test email sending functionality"""
    try:
        result = send_payment_confirmation(
            to_email=recipient,
            payment_id="TEST-123",
            amount=99.99,
            service_name="Email Test Service"
        )
        
        if result:
            return {"status": "success", "message": f"Test email sent to {recipient}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send test email")
    except Exception as e:
        log_error(f"Error in test-email endpoint: {str(e)}")
        log_error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error sending test email: {str(e)}")


# Diagnostic endpoint
@app.get("/check-smtp-config/")
async def check_smtp_config():
    """Check SMTP configuration"""
    config = EmailConfig()
    
    # Check if credentials are set
    credentials_set = bool(config.smtp_username and config.smtp_password)
    
    # Test SMTP connection without sending an email
    connection_success = False
    error_message = None
    
    if credentials_set:
        try:
            log_info(f"Testing connection to {config.smtp_server}:{config.smtp_port}")
            server = smtplib.SMTP(config.smtp_server, config.smtp_port, timeout=10)
            server.set_debuglevel(1)
            
            # Send EHLO
            log_info("Sending EHLO command")
            server.ehlo()
            
            # Start TLS
            log_info("Starting TLS encryption")
            server.starttls()
            
            # Re-send EHLO
            log_info("Sending EHLO command after STARTTLS")
            server.ehlo()
            
            # Try login
            log_info(f"Testing login with username: {config.smtp_username}")
            server.login(config.smtp_username, config.smtp_password)
            
            # Close connection
            log_info("Closing SMTP connection")
            server.quit()
            
            connection_success = True
        except Exception as e:
            error_message = str(e)
            log_error(f"SMTP connection test failed: {error_message}")
            log_error(traceback.format_exc())
    
    return {
        "smtp_server": config.smtp_server,
        "smtp_port": config.smtp_port,
        "credentials_set": credentials_set,
        "connection_success": connection_success,
        "error_message": error_message if not connection_success else None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
