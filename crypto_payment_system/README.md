# Crypto Payment System

An automated system for processing cryptocurrency payments with manual confirmation.

## Features

- Generate payment links with specific amounts and cryptocurrency networks
- Send payment links to clients via email
- Handle payment confirmations with QR codes
- Support for multiple cryptocurrency networks (Bitcoin, Ethereum, BNB, Tron, Solana)
- Track transaction statuses
- Protocol signing by clients
- Admin console for wallet configuration
- Trust Wallet integration

## Installation

1. Clone the repository:
```
git clone https://github.com/your-username/crypto-payment-system.git
cd crypto-payment-system
```

2. Create and activate a virtual environment:
```
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install the required dependencies:
```
pip install -r requirements.txt
```

4. Create a .env file:
```
cp .env.example .env
```

5. Edit the .env file with your configuration:
   - Set your wallet addresses
   - Configure email settings
   - Set your Flask secret key

## Running the Application

### Quick Start

The easiest way to start the application is to use the start script:

```
python start.py
```

This will:
1. Start the Flask server
2. Open the landing page in your default web browser
3. Show server status and URLs in the console

### Manual Start

Alternatively, you can run the server manually:

```
python run.py
```

Then open your browser to:
- http://localhost:8080/ - Main application
- http://localhost:8080/landing - Landing page
- http://localhost:8080/admin - Admin console

## Using the Application

### Landing Page

The landing page provides:
- Server status monitoring
- Quick access to all parts of the system
- Overview of supported cryptocurrencies and features

### Email Reports

The system can send daily transaction reports to a specified email address:

1. **Configuration:**
   - Set the `REPORTS_EMAIL` variable in your `.env` file to the email address that should receive reports
   - Make sure your email settings are properly configured for sending emails

2. **Setup Automated Reports:**
   - On Linux/macOS: Run `bash setup_reports.sh` to set up a daily cron job
   - On Windows: Run `setup_reports.bat` to set up a daily scheduled task
   - Reports will be sent at 00:05 AM every day

3. **Manual Report Generation:**
   - Run `python send_reports.py` to generate and send a report immediately
   
4. **Report Contents:**
   - List of all transactions from the past 24 hours
   - Transaction details including ID, amount, network, status, etc.
   - Summary of completed payments by cryptocurrency network
   - CSV attachment for easy record keeping and analysis

### Configuring Wallet Addresses

You can configure your wallet addresses in several ways:

1. **Via the Admin Console:**
   - Go to the Admin Console page
   - In the "Wallet Settings" tab, configure your wallet addresses for each network

2. **Via Environment Variables:**
   - Edit the `.env` file to specify wallet addresses
   - Use the following format:
   ```
   WALLET_ADDRESS_BITCOIN=your_bitcoin_address
   WALLET_ADDRESS_ETHEREUM=your_ethereum_address
   WALLET_ADDRESS_BNB=your_bnb_address
   WALLET_ADDRESS_TRON=your_tron_address
   WALLET_ADDRESS_SOLANA=your_solana_address
   ```
   - Run `python update_wallets.py` to update the database with these addresses

3. **Directly in the Database:**
   - The addresses are stored in the `wallet_address` table

### Creating a Payment Link

1. Navigate to the "Create Payment Link" page
2. Enter the payment amount
3. Enter the client's email address
4. Select the cryptocurrency network
5. Click "Generate Payment Link"
6. The system will create a unique payment link and send it to the client's email

### Client Payment Process

1. The client receives an email with the payment link
2. The client clicks on the link which opens the payment confirmation page
3. The client sees the payment details (amount, network, recipient address)
4. The client sends the payment from their cryptocurrency wallet to the provided address
5. After sending the payment, the client clicks "Sign Protocol"
6. The system marks the transaction as completed

### Using the Admin Console

1. Go to the Admin Console page
2. In the "Wallet Settings" tab, configure your wallet addresses for each network
3. In the "Quick Payment" tab, generate payment links quickly
4. View recent transactions and their statuses

## Deployment

For detailed deployment instructions, see the [Deployment Guide](deployment.md).

### Local Development

Run the application locally with:
```
python run.py
```

### Production Deployment

For production deployment, you can use:

- Heroku
- PythonAnywhere
- DigitalOcean App Platform
- Docker
- Traditional VPS with Nginx and Gunicorn

## Environment Variables

The application uses the following environment variables:

- `FLASK_ENV`: Set to `development` or `production`
- `SECRET_KEY`: Secret key for Flask
- `DATABASE_URL`: Database connection URL (if not using SQLite)
- `EMAIL_SERVER`: SMTP server address
- `EMAIL_PORT`: SMTP server port
- `EMAIL_USERNAME`: Email username
- `EMAIL_PASSWORD`: Email password
- `EMAIL_SENDER`: Email sender address
- `HOST`: Host address to bind the server (default: 0.0.0.0)
- `PORT`: Port to run the server on (default: 8080)

## Security Considerations

- Always use HTTPS in production
- Implement proper access controls for the admin pages
- Regularly update dependencies
- Validate all input data
- Consider adding user authentication for enhanced security

## License

This project is licensed under the MIT License - see the LICENSE file for details. 