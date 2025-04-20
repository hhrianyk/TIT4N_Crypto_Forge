import requests
import time
import json
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='blockchain_verifier.log'
)
logger = logging.getLogger('blockchain_verifier')

class BlockchainVerifier:
    """Class to verify cryptocurrency transactions on various blockchains"""
    
    def __init__(self, api_keys=None):
        self.api_keys = api_keys or {}
        # Initialize API endpoints
        self.api_endpoints = {
            'bitcoin': 'https://blockchain.info/rawaddr/{address}',
            'ethereum': 'https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=desc&apikey={api_key}',
            'bnb': 'https://api.bscscan.com/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=desc&apikey={api_key}',
            'tron': 'https://apilist.tronscan.org/api/transaction?address={address}&count=30&start=0',
            'solana': 'https://public-api.solscan.io/account/transactions?account={address}&limit=20'
        }
    
    def _get_api_key(self, network):
        """Get API key for the specified network"""
        return self.api_keys.get(network, '')
    
    def _format_address(self, address, network):
        """Format address according to network requirements"""
        return address.strip()
    
    def _check_transaction_bitcoin(self, address, amount, tx_data, max_age_minutes=30):
        """Check if there's a matching Bitcoin transaction"""
        try:
            for tx in tx_data.get('txs', []):
                # Check if transaction is recent
                tx_time = datetime.fromtimestamp(tx.get('time', 0))
                if datetime.now() - tx_time > timedelta(minutes=max_age_minutes):
                    continue
                
                # Check for incoming transactions
                for output in tx.get('out', []):
                    if output.get('addr') == address and output.get('value', 0) / 100000000 >= float(amount):
                        return {
                            'success': True,
                            'tx_hash': tx.get('hash'),
                            'amount': output.get('value') / 100000000,
                            'timestamp': tx_time.isoformat()
                        }
            return {'success': False, 'message': 'No matching transaction found'}
        except Exception as e:
            logger.error(f"Error checking Bitcoin transaction: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def _check_transaction_ethereum(self, address, amount, tx_data, max_age_minutes=30):
        """Check if there's a matching Ethereum transaction"""
        try:
            if tx_data.get('status') != '1':
                return {'success': False, 'message': 'API error: ' + tx_data.get('message', 'Unknown error')}
            
            for tx in tx_data.get('result', []):
                # Check if transaction is recent
                tx_time = datetime.fromtimestamp(int(tx.get('timeStamp', 0)))
                if datetime.now() - tx_time > timedelta(minutes=max_age_minutes):
                    continue
                
                # Check if transaction is to our address and value matches
                if tx.get('to', '').lower() == address.lower() and float(tx.get('value', 0)) / 1e18 >= float(amount):
                    return {
                        'success': True,
                        'tx_hash': tx.get('hash'),
                        'amount': float(tx.get('value')) / 1e18,
                        'timestamp': tx_time.isoformat()
                    }
            return {'success': False, 'message': 'No matching transaction found'}
        except Exception as e:
            logger.error(f"Error checking Ethereum transaction: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def _check_transaction_bnb(self, address, amount, tx_data, max_age_minutes=30):
        """Check if there's a matching BNB transaction (similar to Ethereum)"""
        return self._check_transaction_ethereum(address, amount, tx_data, max_age_minutes)
    
    def _check_transaction_tron(self, address, amount, tx_data, max_age_minutes=30):
        """Check if there's a matching Tron transaction"""
        try:
            for tx in tx_data.get('data', []):
                if tx.get('toAddress') == address and float(tx.get('amount', 0)) / 1e6 >= float(amount):
                    # Tron timestamps are in milliseconds
                    tx_time = datetime.fromtimestamp(int(tx.get('timestamp', 0)) / 1000)
                    if datetime.now() - tx_time > timedelta(minutes=max_age_minutes):
                        continue
                    
                    return {
                        'success': True,
                        'tx_hash': tx.get('hash'),
                        'amount': float(tx.get('amount')) / 1e6,
                        'timestamp': tx_time.isoformat()
                    }
            return {'success': False, 'message': 'No matching transaction found'}
        except Exception as e:
            logger.error(f"Error checking Tron transaction: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def _check_transaction_solana(self, address, amount, tx_data, max_age_minutes=30):
        """Check if there's a matching Solana transaction"""
        try:
            for tx in tx_data:
                # Solana transaction data structure is more complex
                # This is a simplified check and may need to be adjusted
                tx_time = datetime.fromtimestamp(int(tx.get('blockTime', 0)))
                if datetime.now() - tx_time > timedelta(minutes=max_age_minutes):
                    continue
                
                for instruction in tx.get('meta', {}).get('innerInstructions', []):
                    for inner in instruction.get('instructions', []):
                        if inner.get('parsed', {}).get('type') == 'transfer':
                            info = inner.get('parsed', {}).get('info', {})
                            if info.get('destination') == address and float(info.get('lamports', 0)) / 1e9 >= float(amount):
                                return {
                                    'success': True,
                                    'tx_hash': tx.get('signature'),
                                    'amount': float(info.get('lamports')) / 1e9,
                                    'timestamp': tx_time.isoformat()
                                }
            return {'success': False, 'message': 'No matching transaction found'}
        except Exception as e:
            logger.error(f"Error checking Solana transaction: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def verify_transaction(self, network, address, amount, max_age_minutes=30, simulation_mode=True):
        """
        Verify if a transaction of the specified amount has been sent to the address
        on the specified network within the last max_age_minutes.
        
        In simulation mode, it will return success without actually checking the blockchain.
        """
        # For development/testing - simulate successful verification
        if simulation_mode:
            logger.info(f"SIMULATION MODE: Simulating successful transaction for {amount} {network} to {address}")
            return {
                'success': True,
                'tx_hash': 'simulated_tx_' + secrets.token_hex(16),
                'amount': float(amount),
                'timestamp': datetime.now().isoformat(),
                'simulation': True
            }
        
        try:
            # Format address for the specific network
            formatted_address = self._format_address(address, network)
            
            # Get API endpoint and replace placeholders
            api_endpoint = self.api_endpoints.get(network, '')
            if not api_endpoint:
                return {'success': False, 'message': f'Unsupported network: {network}'}
            
            api_endpoint = api_endpoint.format(
                address=formatted_address,
                api_key=self._get_api_key(network)
            )
            
            # Make API request
            response = requests.get(api_endpoint)
            if response.status_code != 200:
                return {'success': False, 'message': f'API error: {response.status_code}'}
            
            tx_data = response.json()
            
            # Call the appropriate transaction checker based on network
            if network == 'bitcoin':
                return self._check_transaction_bitcoin(formatted_address, amount, tx_data, max_age_minutes)
            elif network == 'ethereum':
                return self._check_transaction_ethereum(formatted_address, amount, tx_data, max_age_minutes)
            elif network == 'bnb':
                return self._check_transaction_bnb(formatted_address, amount, tx_data, max_age_minutes)
            elif network == 'tron':
                return self._check_transaction_tron(formatted_address, amount, tx_data, max_age_minutes)
            elif network == 'solana':
                return self._check_transaction_solana(formatted_address, amount, tx_data, max_age_minutes)
            else:
                return {'success': False, 'message': f'Unsupported network: {network}'}
                
        except Exception as e:
            logger.error(f"Error verifying {network} transaction: {str(e)}")
            return {'success': False, 'message': str(e)}

# Example usage
if __name__ == "__main__":
    # Example API keys (replace with your actual API keys)
    api_keys = {
        'ethereum': 'YOUR_ETHERSCAN_API_KEY',
        'bnb': 'YOUR_BSCSCAN_API_KEY'
    }
    
    verifier = BlockchainVerifier(api_keys)
    
    # Example verification (simulated)
    result = verifier.verify_transaction(
        network='ethereum',
        address='0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        amount=0.1,
        simulation_mode=True
    )
    
    print(json.dumps(result, indent=2)) 