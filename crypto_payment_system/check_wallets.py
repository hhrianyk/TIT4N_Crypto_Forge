#!/usr/bin/env python
import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('wallet_checker')

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

# Define WalletAddress model (simplified version of the one in app.py)
class WalletAddress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    network = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=False)

def check_wallets():
    """Check current wallet addresses in the database"""
    with app.app_context():
        wallets = WalletAddress.query.all()
        
        if not wallets:
            print("No wallet addresses found in the database.")
            return
        
        print("\n=== Current Wallet Addresses ===")
        print("--------------------------------")
        
        for wallet in wallets:
            print(f"{wallet.network.upper()}: {wallet.address}")
        
        print("--------------------------------\n")

if __name__ == "__main__":
    check_wallets() 