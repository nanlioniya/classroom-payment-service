from fastapi import FastAPI, HTTPException
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Set up basic logging configuration
logging.basicConfig(level=logging.INFO)

# If you have already set up logging, you can import it
try:
    from logger import log_info, log_error
except ImportError:
    # If import fails, create a simple logging function
    log_info = logging.info
    log_error = logging.error
    log_warning = logging.warning

class EmailConfig:
    """Email configuration class"""
    def __init__(self):
        # Mailtrap configuration
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.mailtrap.io")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 2525))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.default_sender = os.environ.get("DEFAULT_SENDER", "payment@example.com")
        
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
            # Connect to the Mailtrap SMTP server
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.sendmail(
                    msg["From"],
                    to_emails,
                    msg.as_string()
                )
            log_info(f"Email sent to {', '.join(to_emails)}")
            return True
        except Exception as e:
            log_error(f"Error sending email: {str(e)}")
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
        subject = f"Payment Failure Notification #{payment_id}"
        
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
