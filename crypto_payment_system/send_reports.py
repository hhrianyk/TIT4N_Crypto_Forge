#!/usr/bin/env python
import os
import sys
from datetime import datetime, timedelta
import csv
import io
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('reports_sender')

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    logger.error(".env file not found. Please create it first.")
    sys.exit(1)

# Import configuration
from config import config

# Create Flask app
app = Flask(__name__)

# Configure the app based on environment
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

# Initialize database
db = SQLAlchemy(app)

# Import email service
from email_service import EmailService

class Transaction(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    network = db.Column(db.String(20), nullable=False)
    client_email = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, completed
    tx_hash = db.Column(db.String(100), nullable=True)  # blockchain transaction hash
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def generate_daily_report():
    """Generate daily report for the last 24 hours"""
    with app.app_context():
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        # Get all transactions from the last 24 hours
        transactions = Transaction.query.filter(Transaction.created_at >= yesterday).all()
        
        if not transactions:
            logger.info("No transactions found in the last 24 hours")
            return None
        
        # Prepare CSV report
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        
        # Write header
        csv_writer.writerow([
            'Transaction ID', 
            'Amount', 
            'Network', 
            'Client Email', 
            'Status', 
            'Transaction Hash', 
            'Created At', 
            'Updated At', 
            'Description'
        ])
        
        # Write data
        total_amount_by_network = {}
        for transaction in transactions:
            csv_writer.writerow([
                transaction.id,
                transaction.amount,
                transaction.network,
                transaction.client_email,
                transaction.status,
                transaction.tx_hash or 'N/A',
                transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                transaction.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                transaction.description or 'N/A'
            ])
            
            # Track total amounts by network
            if transaction.network not in total_amount_by_network:
                total_amount_by_network[transaction.network] = 0
            
            if transaction.status == 'completed':
                total_amount_by_network[transaction.network] += transaction.amount
        
        # Add summary at the end
        csv_writer.writerow([])
        csv_writer.writerow(['SUMMARY'])
        csv_writer.writerow(['Network', 'Total Completed Amount'])
        
        for network, amount in total_amount_by_network.items():
            csv_writer.writerow([network, amount])
        
        return csv_buffer.getvalue()

def send_report():
    """Send daily report via email"""
    # Get reports email from environment variables
    reports_email = os.environ.get('REPORTS_EMAIL')
    
    if not reports_email:
        logger.error("REPORTS_EMAIL is not set in the environment variables")
        return False
    
    # Generate report
    report_data = generate_daily_report()
    
    if not report_data:
        logger.info("No report data to send")
        return False
    
    # Create email service
    email_service = EmailService(
        server=os.environ.get('EMAIL_SERVER'),
        port=int(os.environ.get('EMAIL_PORT', 587)),
        username=os.environ.get('EMAIL_USERNAME'),
        password=os.environ.get('EMAIL_PASSWORD'),
        sender=os.environ.get('EMAIL_SENDER'),
        use_background_thread=False
    )
    
    # Prepare email content
    today = datetime.utcnow().strftime('%Y-%m-%d')
    subject = f"Daily Crypto Payment Report - {today}"
    
    # Create HTML body with the CSV data as a table
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
            <h2 style="color: #3498db; text-align: center;">Daily Crypto Payment Report</h2>
            <p><strong>Date:</strong> {today}</p>
            <p>Please find attached the daily transaction report.</p>
            <p>The report includes all transactions from the past 24 hours with a summary of completed payments by network.</p>
            <p style="margin-top: 30px; font-size: 12px; color: #777; text-align: center;">
                This is an automated report. Please do not reply to this email.
            </p>
        </div>
    </body>
    </html>
    """
    
    # Convert CSV to attachment
    from email.mime.application import MIMEApplication
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    msg = MIMEMultipart()
    msg.attach(MIMEText(body_html, 'html'))
    
    attachment = MIMEApplication(report_data.encode('utf-8'))
    attachment.add_header('Content-Disposition', 'attachment', filename=f'crypto_payment_report_{today}.csv')
    msg.attach(attachment)
    
    # Send email
    try:
        if not email_service.server or not email_service.username or not email_service.password or not email_service.sender:
            logger.error("Email configuration is incomplete. Please check your .env file.")
            return False
        
        sent = email_service._send_email_direct(
            to_email=reports_email,
            subject=subject,
            body_html=body_html,
            mime_message=msg
        )
        
        if sent:
            logger.info(f"Daily report sent to {reports_email}")
            return True
        else:
            logger.error(f"Failed to send daily report to {reports_email}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending report: {str(e)}")
        return False

# Add ability to send direct email with attachment
def patch_email_service():
    """Patch the EmailService class to support attachments"""
    original_send_email_direct = EmailService._send_email_direct
    
    def patched_send_email_direct(self, to_email, subject, body_html, cc=None, bcc=None, reply_to=None, mime_message=None):
        if mime_message:
            retries = 0
            
            while retries <= self.max_retries:
                try:
                    if mime_message['From'] is None:
                        mime_message['From'] = self.sender
                    if mime_message['To'] is None:
                        mime_message['To'] = to_email
                    if mime_message['Subject'] is None:
                        mime_message['Subject'] = subject
                    
                    recipients = [to_email]
                    if cc:
                        recipients.extend(cc.split(','))
                    if bcc:
                        recipients.extend(bcc.split(','))
                    
                    server = smtplib.SMTP(self.server, self.port)
                    server.starttls()
                    server.login(self.username, self.password)
                    server.sendmail(self.sender, recipients, mime_message.as_string())
                    server.quit()
                    
                    logger.info(f"Email with attachment sent successfully to {to_email}")
                    return True
                    
                except Exception as e:
                    retries += 1
                    logger.warning(f"Error sending email with attachment to {to_email} (attempt {retries}/{self.max_retries}): {str(e)}")
                    
                    if retries <= self.max_retries:
                        time.sleep(self.retry_delay)
            
            logger.error(f"Failed to send email with attachment to {to_email} after {self.max_retries} attempts")
            return False
        else:
            # Call the original method for regular emails
            return original_send_email_direct(self, to_email, subject, body_html, cc, bcc, reply_to)
    
    # Apply the patch
    EmailService._send_email_direct = patched_send_email_direct

if __name__ == "__main__":
    import smtplib
    import time
    
    # Apply patch for sending attachments
    patch_email_service()
    
    logger.info("Starting daily report generation")
    success = send_report()
    
    if success:
        logger.info("Daily report sent successfully")
        sys.exit(0)
    else:
        logger.error("Failed to send daily report")
        sys.exit(1) 