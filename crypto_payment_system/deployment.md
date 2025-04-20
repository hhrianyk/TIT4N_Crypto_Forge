# Deployment Guide

This document provides instructions for deploying the Crypto Payment System to various hosting platforms.

## Prerequisites

Before deploying, make sure you have:

1. Created a `.env` file with your configuration (use `.env.example` as a template)
2. Tested your application locally
3. Set up your database (if using a different one than SQLite)
4. Configured your email settings

## Local Development

To run the application locally:

```bash
# Navigate to the project directory
cd crypto_payment_system

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file
cp .env.example .env
# Edit .env with your configuration

# Run the application
python run.py
```

## Deployment to Heroku

1. Create a Heroku account and install the Heroku CLI
2. Log in to Heroku:
   ```bash
   heroku login
   ```

3. Create a new Heroku app:
   ```bash
   heroku create your-app-name
   ```

4. Set environment variables:
   ```bash
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY=your_secure_secret_key
   heroku config:set EMAIL_SERVER=your_email_server
   heroku config:set EMAIL_PORT=your_email_port
   heroku config:set EMAIL_USERNAME=your_email_username
   heroku config:set EMAIL_PASSWORD=your_email_password
   heroku config:set EMAIL_SENDER=your_email_sender
   ```

5. If using PostgreSQL, add the database:
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   ```

6. Deploy your application:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git push heroku main
   ```

7. Open your application:
   ```bash
   heroku open
   ```

## Deployment to PythonAnywhere

1. Sign up for a PythonAnywhere account

2. Upload your code:
   - Use the Files tab to upload a zip of your project, or
   - Set up Git and clone your repository

3. Set up a virtual environment:
   ```bash
   mkvirtualenv --python=python3.9 myenv
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your configuration

5. Configure a Web App:
   - Go to the Web tab and add a new web app
   - Choose "Manual Configuration" and select Python version
   - Set the virtual environment path
   - Configure the WSGI file to point to your `wsgi.py`

6. Set up environment variables:
   - Add them to the WSGI configuration file
   - Or modify the `wsgi.py` to load them from a file

## Deployment to DigitalOcean App Platform

1. Create a DigitalOcean account and create a new App

2. Connect your repository or upload your code

3. Configure the App:
   - Set the environment to Python
   - Add environment variables from your `.env` file
   - Set the build command: `pip install -r requirements.txt`
   - Set the run command: `gunicorn wsgi:application`

4. Deploy your application

## Deployment with Docker

1. Create a Dockerfile:
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   ENV FLASK_APP=app.py
   ENV FLASK_ENV=production
   
   CMD gunicorn wsgi:application
   ```

2. Build and run the Docker image:
   ```bash
   docker build -t crypto-payment-system .
   docker run -p 8000:8000 --env-file .env crypto-payment-system
   ```

## Deployment with Nginx and Gunicorn (VPS)

1. Set up a VPS with Ubuntu or similar

2. Install required packages:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv nginx
   ```

3. Clone your repository and set up the environment:
   ```bash
   git clone your-repository
   cd your-repository
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your configuration

5. Set up Gunicorn service:
   ```
   # /etc/systemd/system/crypto-payment.service
   [Unit]
   Description=Gunicorn instance to serve crypto payment system
   After=network.target
   
   [Service]
   User=your_user
   Group=www-data
   WorkingDirectory=/path/to/your/app
   Environment="PATH=/path/to/your/app/venv/bin"
   EnvironmentFile=/path/to/your/app/.env
   ExecStart=/path/to/your/app/venv/bin/gunicorn --workers 3 --bind unix:crypto-payment.sock -m 007 wsgi:application
   
   [Install]
   WantedBy=multi-user.target
   ```

6. Configure Nginx:
   ```
   # /etc/nginx/sites-available/crypto-payment
   server {
       listen 80;
       server_name your_domain.com;
   
       location / {
           include proxy_params;
           proxy_pass http://unix:/path/to/your/app/crypto-payment.sock;
       }
   }
   ```

7. Enable and start services:
   ```bash
   sudo ln -s /etc/nginx/sites-available/crypto-payment /etc/nginx/sites-enabled
   sudo systemctl start crypto-payment
   sudo systemctl enable crypto-payment
   sudo systemctl restart nginx
   ```

8. Set up SSL with Certbot:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your_domain.com
   ```

## Database Migration (Optional)

If you need to migrate from SQLite to a production database:

1. For PostgreSQL, install the adapter:
   ```bash
   pip install psycopg2-binary
   ```

2. For MySQL, install the adapter:
   ```bash
   pip install mysqlclient
   ```

3. Set the `DATABASE_URL` environment variable:
   - PostgreSQL: `postgresql://username:password@host:port/database`
   - MySQL: `mysql://username:password@host:port/database`

4. When switching databases, you'll need to recreate your tables:
   ```python
   with app.app_context():
       db.create_all()
   ```

## Monitoring and Maintenance

- Set up logging to a file or service
- Configure regular backups of your database
- Monitor application performance
- Set up alerts for errors or performance issues 