import logging
import time
import threading
import json
import secrets
from datetime import datetime, timedelta
from blockchain_verifier import BlockchainVerifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='payment_processor.log'
)
logger = logging.getLogger('payment_processor')

class PaymentProcessor:
    """Class to automatically process and verify cryptocurrency payments"""
    
    def __init__(self, db, api_keys=None, check_interval=60, simulation_mode=True):
        """
        Initialize the payment processor
        
        Args:
            db: SQLAlchemy database object
            api_keys: Dictionary of API keys for blockchain explorers
            check_interval: How often to check for pending transactions (in seconds)
            simulation_mode: If True, automatically approve payments without blockchain check
        """
        self.db = db
        self.check_interval = check_interval
        self.simulation_mode = simulation_mode
        self.verifier = BlockchainVerifier(api_keys)
        self.running = False
        self.thread = None
        self.Transaction = None  # Will be set when start() is called
        self.WalletAddress = None  # Will be set when start() is called
    
    def _load_models(self):
        """Load database models from app context"""
        # These imports are kept local to prevent circular imports
        from app import Transaction, WalletAddress
        self.Transaction = Transaction
        self.WalletAddress = WalletAddress
    
    def get_pending_transactions(self):
        """Get all transactions with 'confirmed' status that need verification"""
        try:
            return self.Transaction.query.filter_by(status='confirmed').all()
        except Exception as e:
            logger.error(f"Error fetching pending transactions: {str(e)}")
            return []
    
    def get_wallet_address(self, network):
        """Get wallet address for the specified network"""
        try:
            wallet = self.WalletAddress.query.filter_by(network=network).first()
            return wallet.address if wallet else None
        except Exception as e:
            logger.error(f"Error fetching wallet address for {network}: {str(e)}")
            return None
    
    def verify_transaction(self, transaction):
        """
        Verify a single transaction by checking the blockchain
        
        Args:
            transaction: Transaction object from database
        
        Returns:
            dict: Verification result
        """
        try:
            wallet_address = self.get_wallet_address(transaction.network)
            if not wallet_address:
                return {'success': False, 'message': f"No wallet address found for {transaction.network}"}
            
            # Use the blockchain verifier to check if the transaction exists
            verification_result = self.verifier.verify_transaction(
                network=transaction.network,
                address=wallet_address,
                amount=transaction.amount,
                max_age_minutes=60,  # Look for transactions in the last hour
                simulation_mode=self.simulation_mode
            )
            
            # Update transaction with verification details
            if verification_result.get('success'):
                transaction.status = 'completed'
                transaction.updated_at = datetime.utcnow()
                # Can add more fields to store tx_hash, etc.
                
                try:
                    self.db.session.commit()
                    logger.info(f"Transaction {transaction.id} verified and marked as completed")
                except Exception as e:
                    self.db.session.rollback()
                    logger.error(f"Database error updating transaction {transaction.id}: {str(e)}")
                    return {'success': False, 'message': f"Database error: {str(e)}"}
            
            return verification_result
        except Exception as e:
            logger.error(f"Error verifying transaction {transaction.id}: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def process_pending_transactions(self):
        """Process all pending transactions"""
        pending_transactions = self.get_pending_transactions()
        if not pending_transactions:
            logger.info("No pending transactions to process")
            return
        
        logger.info(f"Processing {len(pending_transactions)} pending transactions")
        
        for transaction in pending_transactions:
            logger.info(f"Verifying transaction {transaction.id} for {transaction.amount} {transaction.network}")
            result = self.verify_transaction(transaction)
            
            if result.get('success'):
                logger.info(f"Transaction {transaction.id} successfully verified")
            else:
                logger.warning(f"Transaction {transaction.id} verification failed: {result.get('message')}")
    
    def _processor_loop(self):
        """Main processing loop that runs in a separate thread"""
        logger.info("Payment processor started")
        
        while self.running:
            try:
                self.process_pending_transactions()
            except Exception as e:
                logger.error(f"Error in processor loop: {str(e)}")
            
            # Sleep for the check interval before processing again
            time.sleep(self.check_interval)
        
        logger.info("Payment processor stopped")
    
    def start(self):
        """Start the payment processor in a separate thread"""
        if self.thread and self.thread.is_alive():
            logger.warning("Payment processor is already running")
            return
        
        self._load_models()
        self.running = True
        self.thread = threading.Thread(target=self._processor_loop)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("Payment processor started in background thread")
        return True
    
    def stop(self):
        """Stop the payment processor"""
        if not self.thread or not self.thread.is_alive():
            logger.warning("Payment processor is not running")
            return
        
        logger.info("Stopping payment processor...")
        self.running = False
        self.thread.join(timeout=5.0)
        
        if self.thread.is_alive():
            logger.warning("Payment processor thread did not stop gracefully")
        else:
            logger.info("Payment processor stopped successfully")
        
        return True

# Example usage
if __name__ == "__main__":
    from app import app, db, Transaction, WalletAddress
    
    # Example API keys (replace with your actual API keys)
    api_keys = {
        'ethereum': 'YOUR_ETHERSCAN_API_KEY',
        'bnb': 'YOUR_BSCSCAN_API_KEY'
    }
    
    with app.app_context():
        processor = PaymentProcessor(
            db=db,
            api_keys=api_keys,
            check_interval=30,  # Check every 30 seconds
            simulation_mode=True  # Use simulation mode for testing
        )
        
        # Start the processor
        processor.start()
        
        try:
            # Keep the script running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # Stop the processor on Ctrl+C
            processor.stop() 