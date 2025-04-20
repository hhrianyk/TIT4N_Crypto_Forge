from flask import Flask, request, redirect, jsonify, render_template, url_for, flash, send_from_directory
import uuid
import secrets
from datetime import datetime
import os
import json
from urllib.parse import urlencode
from dotenv import load_dotenv
import logging
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log',
    filemode='a'
)
logger = logging.getLogger('crypto_payment_app')

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Import configuration
from config import config

# Create Flask app
app = Flask(__name__)

# Configure the app based on environment
env = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[env])

# Import our services
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from blockchain_verifier import BlockchainVerifier
from email_service import EmailService

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)

# Initialize services
email_service = EmailService(
    server=app.config.get('EMAIL_SERVER'),
    port=app.config.get('EMAIL_PORT'),
    username=app.config.get('EMAIL_USERNAME'),
    password=app.config.get('EMAIL_PASSWORD'),
    sender=app.config.get('EMAIL_SENDER'),
    use_background_thread=True
)

# Database models
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

    def __repr__(self):
        return f'<Transaction {self.id}>'
    
    def to_dict(self):
        """Convert transaction to dictionary for API responses"""
        return {
            'id': self.id,
            'amount': self.amount,
            'network': self.network,
            'client_email': self.client_email,
            'description': self.description,
            'status': self.status,
            'tx_hash': self.tx_hash,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class WalletAddress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    network = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<WalletAddress {self.network}: {self.address}>'

class BlockchainAPIKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    network = db.Column(db.String(20), unique=True, nullable=False)
    api_key = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<BlockchainAPIKey {self.network}>'

# Initialize payment processor
from payment_processor import PaymentProcessor

# Create tables and initialize data
def initialize_app():
    db.create_all()
    
    # Initialize default wallet addresses if they don't exist
    default_wallets = {
        'bitcoin': os.environ.get('WALLET_ADDRESS_BITCOIN', 'your_bitcoin_wallet_address'),
        'ethereum': os.environ.get('WALLET_ADDRESS_ETHEREUM', 'your_ethereum_wallet_address'),
        'bnb': os.environ.get('WALLET_ADDRESS_BNB', 'your_bnb_wallet_address'),
        'tron': os.environ.get('WALLET_ADDRESS_TRON', 'your_tron_wallet_address'),
        'solana': os.environ.get('WALLET_ADDRESS_SOLANA', 'your_solana_wallet_address')
    }
    
    for network, address in default_wallets.items():
        existing = WalletAddress.query.filter_by(network=network).first()
        if not existing:
            wallet = WalletAddress(network=network, address=address)
            db.session.add(wallet)
        else:
            # Update existing wallet addresses with values from environment variables
            existing.address = address
    
    db.session.commit()
    
    # Start the email service
    email_service.start()
    
    # Start the payment processor
    api_keys = {}
    api_key_records = BlockchainAPIKey.query.all()
    for key in api_key_records:
        api_keys[key.network] = key.api_key
    
    global payment_processor
    payment_processor = PaymentProcessor(
        db=db,
        api_keys=api_keys,
        check_interval=60,  # Check every 60 seconds
        simulation_mode=os.environ.get('SIMULATION_MODE', 'true').lower() == 'true'
    )
    payment_processor.start()
    
    logger.info("Application initialized successfully")

# Call initialize_app with the app context
with app.app_context():
    initialize_app()

# Helper functions
def get_wallet_addresses():
    """Get all wallet addresses from database as a dictionary"""
    wallets = WalletAddress.query.all()
    return {wallet.network: wallet.address for wallet in wallets}

def get_api_keys():
    """Get all API keys from database as a dictionary"""
    keys = BlockchainAPIKey.query.all()
    return {key.network: key.api_key for key in keys}

def generate_payment_link(transaction_id, amount, network, description=None):
    """Generate a payment link with transaction ID and amount"""
    base_url = request.host_url.rstrip('/')
    params = {
        'amount': amount,
        'network': network
    }
    if description:
        params['description'] = description
        
    payment_link = f"{base_url}/confirm_payment/{transaction_id}?{urlencode(params)}"
    return payment_link

def generate_trust_wallet_uri(network, address, amount, description=None):
    """Generate a URI compatible with Trust Wallet for direct payment"""
    # Map our network names to Trust Wallet protocol schemes
    network_schemes = {
        'bitcoin': 'bitcoin',
        'ethereum': 'ethereum',
        'bnb': 'bnb',
        'tron': 'tron',
        'solana': 'solana'
    }
    
    scheme = network_schemes.get(network, network)
    params = {'address': address, 'amount': amount}
    if description:
        params['memo'] = description
        
    return f"{scheme}:{address}?{urlencode(params)}"

def send_payment_link_email(to_email, payment_link, amount, network, description=None):
    """Send email with payment link to the client"""
    return email_service.send_payment_link(to_email, payment_link, amount, network, description)

def send_payment_confirmation_email(to_email, transaction_id, amount, network, tx_hash=None):
    """Send payment confirmation email to the client"""
    return email_service.send_payment_confirmation(to_email, transaction_id, amount, network, tx_hash)

# Routes
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/landing')
def landing():
    """Serve the landing page"""
    return send_from_directory('static', 'landing.html')

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard"""
    wallet_addresses = get_wallet_addresses()
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
    return render_template('admin.html', wallets=wallet_addresses, transactions=transactions)

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    """Admin settings page"""
    if request.method == 'POST':
        # Handle API key updates
        api_keys = {}
        for key in request.form:
            if key.endswith('_api_key'):
                network = key.replace('_api_key', '')
                api_keys[network] = request.form[key]
        
        # Update API keys in database
        for network, api_key in api_keys.items():
            if api_key.strip():  # Only update non-empty keys
                existing = BlockchainAPIKey.query.filter_by(network=network).first()
                if existing:
                    existing.api_key = api_key
                else:
                    new_key = BlockchainAPIKey(network=network, api_key=api_key)
                    db.session.add(new_key)
        
        db.session.commit()
        flash('API keys updated successfully', 'success')
        
        # Restart payment processor with new API keys
        if 'payment_processor' in globals():
            payment_processor.stop()
            payment_processor.api_keys = get_api_keys()
            payment_processor.start()
            
        return redirect(url_for('admin_settings'))
    
    # GET request - show form
    api_keys = get_api_keys()
    return render_template('admin_settings.html', api_keys=api_keys)

@app.route('/send_payment_link', methods=['GET', 'POST'])
def send_payment_link():
    """Handle sending payment link to client"""
    if request.method == 'POST':
        amount = request.form.get('amount')
        client_email = request.form.get('client_email')
        network = request.form.get('network', 'ethereum')  # Default to ethereum
        description = request.form.get('description')
        
        # Validate input
        if not amount or not client_email or not network:
            return jsonify({'error': 'Missing required fields'}), 400
        
        try:
            amount = float(amount)
        except ValueError:
            return jsonify({'error': 'Invalid amount'}), 400
            
        wallet_addresses = get_wallet_addresses()
        if network not in wallet_addresses:
            return jsonify({'error': 'Unsupported network'}), 400
        
        # Create transaction record
        transaction_id = str(uuid.uuid4())
        transaction = Transaction(
            id=transaction_id,
            amount=amount,
            network=network,
            client_email=client_email,
            description=description
        )
        db.session.add(transaction)
        db.session.commit()
        
        # Generate and send payment link
        payment_link = generate_payment_link(transaction_id, amount, network, description)
        
        if send_payment_link_email(client_email, payment_link, amount, network, description):
            return jsonify({
                'success': True,
                'message': f'Payment link sent to {client_email}',
                'payment_link': payment_link,
                'transaction_id': transaction_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to send email, but payment link created',
                'payment_link': payment_link,
                'transaction_id': transaction_id
            })
    
    # GET request - show form
    return render_template('send_link.html')

@app.route('/api/generate_link', methods=['POST'])
def api_generate_link():
    """API endpoint to generate payment link"""
    amount = request.form.get('amount')
    client_email = request.form.get('client_email')
    network = request.form.get('network', 'ethereum')
    description = request.form.get('description')
    
    # Validate input
    if not amount or not client_email or not network:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        amount = float(amount)
    except ValueError:
        return jsonify({'error': 'Invalid amount'}), 400
        
    wallet_addresses = get_wallet_addresses()
    if network not in wallet_addresses:
        return jsonify({'error': 'Unsupported network'}), 400
    
    # Create transaction record
    transaction_id = str(uuid.uuid4())
    transaction = Transaction(
        id=transaction_id,
        amount=amount,
        network=network,
        client_email=client_email,
        description=description
    )
    db.session.add(transaction)
    db.session.commit()
    
    # Generate payment link
    payment_link = generate_payment_link(transaction_id, amount, network, description)
    
    return jsonify({
        'success': True,
        'transaction_id': transaction_id,
        'payment_link': payment_link
    })

@app.route('/api/send_email', methods=['POST'])
def api_send_email():
    """API endpoint to send payment link email"""
    data = request.json
    transaction_id = data.get('transaction_id')
    client_email = data.get('client_email')
    payment_link = data.get('payment_link')
    
    if not transaction_id or not client_email or not payment_link:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Get transaction details
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    # Send email
    if send_payment_link_email(client_email, payment_link, transaction.amount, transaction.network, transaction.description):
        return jsonify({
            'success': True,
            'message': f'Email sent to {client_email}'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to send email'
        }), 500

@app.route('/update_wallet_addresses', methods=['POST'])
def update_wallet_addresses():
    """Update wallet addresses"""
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        for network, address in data.items():
            if not address.strip():
                continue
                
            wallet = WalletAddress.query.filter_by(network=network).first()
            if wallet:
                wallet.address = address
            else:
                wallet = WalletAddress(network=network, address=address)
                db.session.add(wallet)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/confirm_payment/<transaction_id>', methods=['GET'])
def confirm_payment(transaction_id):
    """Display payment confirmation page"""
    amount = request.args.get('amount')
    network = request.args.get('network', 'ethereum')
    description = request.args.get('description')
    
    # Retrieve transaction from database
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Verify transaction details match
    if str(transaction.amount) != str(amount) or transaction.network != network:
        return render_template('error.html', message="Invalid transaction details"), 400
    
    if transaction.status != 'pending':
        return render_template('error.html', message="This transaction has already been processed"), 400
    
    # Update transaction status
    transaction.status = 'confirmed'
    db.session.commit()
    
    # Get wallet address
    wallet_addresses = get_wallet_addresses()
    wallet_address = wallet_addresses.get(network)
    
    # Generate Trust Wallet compatible URI
    trust_wallet_uri = generate_trust_wallet_uri(network, wallet_address, amount, description)
    
    # Prepare currency symbols for display
    currency_symbols = {
        'bitcoin': 'BTC',
        'ethereum': 'ETH',
        'bnb': 'BNB',
        'tron': 'TRX',
        'solana': 'SOL'
    }
    
    currency_symbol = currency_symbols.get(network, network.upper())
    
    return render_template(
        'confirm_payment.html',
        transaction_id=transaction_id,
        amount=amount,
        network=network,
        description=description,
        wallet_address=wallet_address,
        trust_wallet_uri=trust_wallet_uri,
        currency_symbol=currency_symbol
    )

@app.route('/sign_protocol/<transaction_id>', methods=['POST'])
@csrf.exempt  # Exempt this route from CSRF (you should implement proper protection)
def sign_protocol(transaction_id):
    """Handle protocol signing and payment completion"""
    transaction = Transaction.query.get_or_404(transaction_id)
    
    if transaction.status != 'confirmed':
        return jsonify({'error': 'Invalid transaction state'}), 400
    
    # In a real implementation, you would verify the actual blockchain transaction here
    # We'll use our blockchain verifier instead of just updating the status
    
    wallet_addresses = get_wallet_addresses()
    wallet_address = wallet_addresses.get(transaction.network)
    
    if not wallet_address:
        return jsonify({'error': f'No wallet address configured for {transaction.network}'}), 400
    
    # Initialize blockchain verifier
    api_keys = get_api_keys()
    verifier = BlockchainVerifier(api_keys)
    
    # Check if there's a real transaction (or simulate in development)
    simulation_mode = os.environ.get('SIMULATION_MODE', 'true').lower() == 'true'
    verification_result = verifier.verify_transaction(
        network=transaction.network,
        address=wallet_address,
        amount=transaction.amount,
        max_age_minutes=60,  # Look for transactions in the last hour
        simulation_mode=simulation_mode
    )
    
    if verification_result.get('success'):
        # Update transaction with verification details
        transaction.status = 'completed'
        transaction.tx_hash = verification_result.get('tx_hash')
        transaction.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Send confirmation email
        send_payment_confirmation_email(
            transaction.client_email,
            transaction.id,
            transaction.amount,
            transaction.network,
            transaction.tx_hash
        )
        
        return jsonify({
            'success': True,
            'message': 'Protocol successfully signed and payment completed',
            'tx_hash': verification_result.get('tx_hash')
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Payment verification failed: ' + verification_result.get('message', 'Unknown error')
        }), 400

@app.route('/admin/transactions')
def view_transactions():
    """Admin view to see all transactions"""
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    return render_template('transactions.html', transactions=transactions)

@app.route('/api/transactions')
def api_transactions():
    """API endpoint to get all transactions"""
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    return jsonify({
        'transactions': [t.to_dict() for t in transactions]
    })

@app.route('/api/server-info')
def server_info():
    """API endpoint to get server information"""
    host = request.host
    wallet_addresses = get_wallet_addresses()
    return jsonify({
        'success': True,
        'host': host,
        'environment': os.environ.get('FLASK_ENV', 'development'),
        'wallet_count': len(wallet_addresses),
        'transaction_count': Transaction.query.count(),
        'automatic_verification': os.environ.get('SIMULATION_MODE', 'true').lower() == 'true'
    })

@app.route('/api/verify-pending')
def api_verify_pending():
    """API endpoint to manually trigger verification of pending transactions"""
    if 'payment_processor' in globals():
        # Trigger a manual check
        threading.Thread(target=payment_processor.process_pending_transactions).start()
        return jsonify({
            'success': True,
            'message': 'Verification process triggered'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Payment processor not initialized'
        }), 500

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', message="Server error, please try again later"), 500

# Cleanup when shutting down
@app.teardown_appcontext
def shutdown_services(exception=None):
    if 'payment_processor' in globals() and hasattr(payment_processor, 'stop'):
        payment_processor.stop()
    
    if hasattr(email_service, 'stop'):
        email_service.stop()

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG']) 