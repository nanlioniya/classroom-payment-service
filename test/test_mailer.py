# test_mailer.py
import pytest
from unittest.mock import patch, MagicMock
import os
import uuid
from mailer_service.main import (
    EmailConfig, 
    EmailSender, 
    EmailTemplates, 
    send_payment_confirmation, 
    send_payment_failed
)

class TestEmailConfig:
    """Test email configuration class"""
    
    def test_email_config_default_values(self):
        """Test default values of EmailConfig"""
        # Use temporary environment variables
        with patch.dict(os.environ, {}, clear=True):
            config = EmailConfig()
            assert config.smtp_server == "smtp.mailtrap.io"
            assert config.smtp_port == 2525
            assert config.smtp_username == ""
            assert config.smtp_password == ""
            assert config.default_sender == "payment@example.com"
    
    def test_email_config_custom_values(self):
        """Test custom values of EmailConfig"""
        # Set temporary environment variables
        env_vars = {
            "SMTP_SERVER": "test.smtp.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "test_user",
            "SMTP_PASSWORD": "test_pass",
            "DEFAULT_SENDER": "test@example.com"
        }
        with patch.dict(os.environ, env_vars):
            config = EmailConfig()
            assert config.smtp_server == "test.smtp.com"
            assert config.smtp_port == 587
            assert config.smtp_username == "test_user"
            assert config.smtp_password == "test_pass"
            assert config.default_sender == "test@example.com"


class TestEmailSender:
    """Test email sender class"""
    
    def setup_method(self):
        """Set up the test environment"""
        # Create test configuration
        self.config = EmailConfig()
        self.config.smtp_server = "test.smtp.com"
        self.config.smtp_port = 587
        self.config.smtp_username = "test_user"
        self.config.smtp_password = "test_pass"
        self.config.default_sender = "test@example.com"
        
        # Create email sender
        self.email_sender = EmailSender(config=self.config)
    
    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending"""
        # Set up mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Send test email
        result = self.email_sender.send_email(
            to_emails=["recipient@example.com"],
            subject="Test Subject",
            html_content="<p>Test HTML Content</p>",
            text_content="Test Text Content"
        )
        
        # Verify the result
        assert result is True
        mock_smtp.assert_called_once_with("test.smtp.com", 587)
        mock_server.login.assert_called_once_with("test_user", "test_pass")
        mock_server.sendmail.assert_called_once()
    
    @patch('smtplib.SMTP')
    def test_send_email_no_recipients(self, mock_smtp):
        """Test case with no recipients"""
        # Send email with no recipients
        result = self.email_sender.send_email(
            to_emails=[],
            subject="Test Subject",
            html_content="<p>Test HTML Content</p>"
        )
        
        # Verify the result
        assert result is False
        mock_smtp.assert_not_called()
    
    @patch('smtplib.SMTP')
    def test_send_email_exception(self, mock_smtp):
        """Test case when an exception occurs during email sending"""
        # Set up mock to raise an exception
        mock_smtp.return_value.__enter__.side_effect = Exception("Test exception")
        
        # Send test email
        result = self.email_sender.send_email(
            to_emails=["recipient@example.com"],
            subject="Test Subject",
            html_content="<p>Test HTML Content</p>"
        )
        
        # Verify the result
        assert result is False


class TestEmailTemplates:
    """Test email template class"""
    
    def test_payment_confirmation_template(self):
        """Test payment confirmation email template"""
        payment_id = str(uuid.uuid4())
        amount = 100.50
        service_name = "Test Service"
        
        subject, html, text = EmailTemplates.payment_confirmation(payment_id, amount, service_name)
        
        # Verify the subject
        assert subject == f"Payment Confirmation #{payment_id}"
        
        # Verify the HTML content
        assert f"<strong>Payment ID:</strong> {payment_id}" in html
        assert f"<strong>Amount:</strong> ${amount:.2f}" in html
        assert f"<strong>Service:</strong> {service_name}" in html
        
        # Verify the plain text content
        assert f"Payment ID: {payment_id}" in text
        assert f"Amount: ${amount:.2f}" in text
        assert f"Service: {service_name}" in text
    
    def test_payment_failed_template(self):
        """Test payment failed email template"""
        payment_id = str(uuid.uuid4())
        amount = 200.75
        reason = "Credit card declined"
        
        subject, html, text = EmailTemplates.payment_failed(payment_id, amount, reason)
        
        # Verify the subject
        assert subject == f"Payment Failed Notification #{payment_id}"
        
        # Verify the HTML content
        assert f"<strong>Payment ID:</strong> {payment_id}" in html
        assert f"<strong>Amount:</strong> ${amount:.2f}" in html
        assert f"<strong>Failure Reason:</strong> {reason}" in html
        
        # Verify the plain text content
        assert f"Payment ID: {payment_id}" in text
        assert f"Amount: ${amount:.2f}" in text
        assert f"Failure Reason: {reason}" in text


class TestMailerFunctions:
    """Test email sending functions"""
    
    @patch('mailer_service.main.email_sender.send_email')
    def test_send_payment_confirmation(self, mock_send_email):
        """Test send_payment_confirmation function"""
        # Set mock return value
        mock_send_email.return_value = True
        
        # Call the function
        result = send_payment_confirmation(
            to_email="customer@example.com",
            payment_id="PAY123",
            amount=150.25,
            service_name="Premium Service"
        )
        
        # Verify the result
        assert result is True
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        assert args[0] == ["customer@example.com"]  # to_emails
        assert "Payment Confirmation #PAY123" in args[1]  # subject
    
    @patch('mailer_service.main.email_sender.send_email')
    def test_send_payment_failed(self, mock_send_email):
        """Test send_payment_failed function"""
        # Set mock return value
        mock_send_email.return_value = True
        
        # Call the function
        result = send_payment_failed(
            to_email="customer@example.com",
            payment_id="PAY456",
            amount=75.50,
            reason="Insufficient balance"
        )
        
        # Verify the result
        assert result is True
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        assert args[0] == ["customer@example.com"]  # to_emails
        assert "Payment Failed Notification #PAY456" in args[1]  # subject

def test_environment_variables():
    """Test if environment variables are loaded correctly"""
    import os
    print("SMTP_USERNAME:", os.environ.get("SMTP_USERNAME"))
    print("SMTP_SERVER:", os.environ.get("SMTP_SERVER"))
    print("SMTP_PORT:", os.environ.get("SMTP_PORT"))
    
    assert os.environ.get("SMTP_USERNAME") == "9c8dce622a3f58"
    assert os.environ.get("SMTP_SERVER") == "sandbox.smtp.mailtrap.io"
    assert os.environ.get("SMTP_PORT") == "2525"