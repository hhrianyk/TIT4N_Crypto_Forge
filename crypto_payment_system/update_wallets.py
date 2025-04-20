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
logger = logging.getLogger('wallet_updater')

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

def update_wallets():
    """Update wallet addresses from environment variables"""
    with app.app_context():
        # Get wallet addresses from environment variables
        wallets = {
            'bitcoin': os.environ.get('WALLET_ADDRESS_BITCOIN'),
            'ethereum': os.environ.get('WALLET_ADDRESS_ETHEREUM'),
            'bnb': os.environ.get('WALLET_ADDRESS_BNB'),
            'tron': os.environ.get('WALLET_ADDRESS_TRON'),
            'solana': os.environ.get('WALLET_ADDRESS_SOLANA')
        }
        
        # Update each wallet address
        for network, address in wallets.items():
            if not address:
                logger.warning(f"No address found for {network} network")
                continue
                
            existing = WalletAddress.query.filter_by(network=network).first()
            if existing:
                logger.info(f"Updating {network} wallet address")
                existing.address = address
            else:
                logger.info(f"Creating new {network} wallet address")
                new_wallet = WalletAddress(network=network, address=address)
                db.session.add(new_wallet)
        
        db.session.commit()
        logger.info("Wallet addresses updated successfully")

if __name__ == "__main__":
    logger.info("Starting wallet address update")
    update_wallets()
    logger.info("Wallet address update completed") 