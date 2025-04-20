import smtplib
import logging
import threading
import time
import os
import queue
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='email_service.log'
)
logger = logging.getLogger('email_service')

class EmailService:
    """
    Service to handle email sending with retry logic and background processing
    """
    
    def __init__(self, server=None, port=None, username=None, password=None, sender=None, 
                 max_retries=3, retry_delay=5, use_background_thread=True):
        """
        Initialize the email service
        
        Args:
            server: SMTP server address
            port: SMTP server port
            username: SMTP username
            password: SMTP password
            sender: Email sender address
            max_retries: Maximum number of retries for failed emails
            retry_delay: Delay between retries in seconds
            use_background_thread: Whether to send emails in a background thread
        """
        # Email server settings
        self.server = server or os.environ.get('EMAIL_SERVER')
        self.port = int(port or os.environ.get('EMAIL_PORT', 587))
        self.username = username or os.environ.get('EMAIL_USERNAME')
        self.password = password or os.environ.get('EMAIL_PASSWORD')
        self.sender = sender or os.environ.get('EMAIL_SENDER')
        
        # Retry settings
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Background thread settings
        self.use_background_thread = use_background_thread
        self.email_queue = queue.Queue()
        self.running = False
        self.thread = None
    
    def _send_email_direct(self, to_email, subject, body_html, cc=None, bcc=None, reply_to=None, mime_message=None):
        """
        Send an email directly (not in background thread)
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body of the email
            cc: Carbon copy recipients (comma-separated string)
            bcc: Blind carbon copy recipients (comma-separated string)
            reply_to: Reply-To email address
            mime_message: Pre-constructed MIMEMultipart message (for attachments)
        
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        retries = 0
        
        while retries <= self.max_retries:
            try:
                if mime_message:
                    # Use the pre-constructed message
                    msg = mime_message
                    # Make sure basic headers are set
                    if 'From' not in msg:
                        msg['From'] = self.sender
                    if 'To' not in msg:
                        msg['To'] = to_email
                    if 'Subject' not in msg:
                        msg['Subject'] = subject
                else:
                    # Construct a new message
                    msg = MIMEMultipart()
                    msg['From'] = self.sender
                    msg['To'] = to_email
                    msg['Subject'] = subject
                    
                    if cc:
                        msg['Cc'] = cc
                    if reply_to:
                        msg['Reply-To'] = reply_to
                    
                    msg.attach(MIMEText(body_html, 'html'))
                
                recipients = [to_email]
                if cc:
                    recipients.extend(cc.split(','))
                if bcc:
                    recipients.extend(bcc.split(','))
                
                server = smtplib.SMTP(self.server, self.port)
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.sender, recipients, msg.as_string())
                server.quit()
                
                logger.info(f"Email sent successfully to {to_email}")
                return True
                
            except Exception as e:
                retries += 1
                logger.warning(f"Error sending email to {to_email} (attempt {retries}/{self.max_retries}): {str(e)}")
                
                if retries <= self.max_retries:
                    time.sleep(self.retry_delay)
        
        logger.error(f"Failed to send email to {to_email} after {self.max_retries} attempts")
        return False
    
    def send_email(self, to_email, subject, body_html, cc=None, bcc=None, reply_to=None):
        """
        Send an email (either directly or in background thread)
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body of the email
            cc: Carbon copy recipients (comma-separated string)
            bcc: Blind carbon copy recipients (comma-separated string)
            reply_to: Reply-To email address
        
        Returns:
            bool: True if email was queued or sent successfully, False otherwise
        """
        if not self.server or not self.username or not self.password or not self.sender:
            logger.error("Email configuration is incomplete")
            return False
        
        if self.use_background_thread:
            # Queue the email for background processing
            self.email_queue.put({
                'to_email': to_email,
                'subject': subject,
                'body_html': body_html,
                'cc': cc,
                'bcc': bcc,
                'reply_to': reply_to
            })
            return True
        else:
            # Send the email directly
            return self._send_email_direct(to_email, subject, body_html, cc, bcc, reply_to)
    
    def send_payment_link(self, to_email, payment_link, amount, network, description=None):
        """
        Send a payment link email
        
        Args:
            to_email: Recipient email address
            payment_link: Payment link URL
            amount: Payment amount
            network: Cryptocurrency network
            description: Payment description (optional)
        
        Returns:
            bool: True if email was queued or sent successfully, False otherwise
        """
        # Network display names
        network_names = {
            'bitcoin': 'Bitcoin (BTC)',
            'ethereum': 'Ethereum (ETH)',
            'bnb': 'Binance Smart Chain (BNB)',
            'tron': 'Tron (TRX)',
            'solana': 'Solana (SOL)'
        }
        
        network_name = network_names.get(network, network.upper())
        subject = f"Payment Request for {amount} {network.upper()}"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #3498db; text-align: center;">Payment Request</h2>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3>Payment Details:</h3>
                    <p><strong>Amount:</strong> {amount} {network.upper()}</p>
                    <p><strong>Network:</strong> {network_name}</p>
                    {f'<p><strong>Description:</strong> {description}</p>' if description else ''}
                </div>
                <p>Please click the link below to process your payment:</p>
                <p style="text-align: center;">
                    <a href="{payment_link}" style="display: inline-block; background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Make Payment</a>
                </p>
                <p style="text-align: center;">Or copy this link:</p>
                <p style="text-align: center; word-break: break-all; background-color: #f8f9fa; padding: 10px; border: 1px solid #ddd; border-radius: 3px;">{payment_link}</p>
                <p style="margin-top: 30px; font-size: 12px; color: #777; text-align: center;">
                    This is an automated payment request. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, body_html)
    
    def send_payment_confirmation(self, to_email, transaction_id, amount, network, tx_hash=None):
        """
        Send a payment confirmation email
        
        Args:
            to_email: Recipient email address
            transaction_id: Transaction ID
            amount: Payment amount
            network: Cryptocurrency network
            tx_hash: Transaction hash (optional)
        
        Returns:
            bool: True if email was queued or sent successfully, False otherwise
        """
        subject = f"Payment Confirmation - {amount} {network.upper()}"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #2ecc71; text-align: center;">Payment Confirmed</h2>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3>Payment Details:</h3>
                    <p><strong>Transaction ID:</strong> {transaction_id}</p>
                    <p><strong>Amount:</strong> {amount} {network.upper()}</p>
                    <p><strong>Network:</strong> {network}</p>
                    {f'<p><strong>Transaction Hash:</strong> {tx_hash}</p>' if tx_hash else ''}
                </div>
                <p style="text-align: center;">Thank you for your payment!</p>
                <p style="margin-top: 30px; font-size: 12px; color: #777; text-align: center;">
                    This is an automated confirmation email. Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, body_html)
    
    def _email_processor_loop(self):
        """Process emails in the queue"""
        logger.info("Email processor started")
        
        while self.running:
            try:
                # Get email from queue with a timeout
                try:
                    email_data = self.email_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Send the email
                try:
                    success = self._send_email_direct(
                        email_data['to_email'],
                        email_data['subject'],
                        email_data['body_html'],
                        email_data.get('cc'),
                        email_data.get('bcc'),
                        email_data.get('reply_to')
                    )
                    
                    if not success:
                        logger.error(f"Failed to send email to {email_data['to_email']}")
                    
                finally:
                    # Mark the task as done regardless of success
                    self.email_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in email processor loop: {str(e)}")
        
        logger.info("Email processor stopped")
    
    def start(self):
        """Start the email processor in a background thread"""
        if not self.use_background_thread:
            logger.info("Background thread is disabled, not starting email processor")
            return False
        
        if self.thread and self.thread.is_alive():
            logger.warning("Email processor is already running")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._email_processor_loop)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("Email processor started in background thread")
        return True
    
    def stop(self):
        """Stop the email processor"""
        if not self.use_background_thread or not self.thread or not self.thread.is_alive():
            logger.warning("Email processor is not running")
            return False
        
        logger.info("Stopping email processor...")
        self.running = False
        self.thread.join(timeout=5.0)
        
        if self.thread.is_alive():
            logger.warning("Email processor thread did not stop gracefully")
        else:
            logger.info("Email processor stopped successfully")
        
        return True

# Example usage
if __name__ == "__main__":
    # Create an email service
    email_service = EmailService(
        server=os.environ.get('EMAIL_SERVER', 'smtp.example.com'),
        port=int(os.environ.get('EMAIL_PORT', 587)),
        username=os.environ.get('EMAIL_USERNAME', 'your_email@example.com'),
        password=os.environ.get('EMAIL_PASSWORD', 'your_password'),
        sender=os.environ.get('EMAIL_SENDER', 'your_email@example.com'),
        use_background_thread=True
    )
    
    # Start the email processor
    email_service.start()
    
    # Send a test payment link
    email_service.send_payment_link(
        to_email="client@example.com",
        payment_link="http://localhost:8080/confirm_payment/123?amount=0.1&network=ethereum",
        amount=0.1,
        network="ethereum",
        description="Test payment"
    )
    
    # Wait for all emails to be sent
    time.sleep(5)
    
    # Stop the email processor
    email_service.stop() 