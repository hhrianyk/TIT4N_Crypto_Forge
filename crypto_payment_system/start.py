import os
import subprocess
import sys
import webbrowser
import time
import signal
import threading
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("Warning: .env file not found. Using default settings.")
    
# Default configuration
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', 8080))
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')

# Get the server URL
server_url = f"http://{HOST}:{PORT}"
landing_url = f"{server_url}/landing"

def start_flask_server():
    """Start the Flask server"""
    print(f"Starting Flask server at {server_url}...")
    
    # Set environment variables for the subprocess
    env = os.environ.copy()
    env['FLASK_APP'] = 'app.py'
    env['FLASK_ENV'] = FLASK_ENV
    env['HOST'] = HOST
    env['PORT'] = str(PORT)
    
    # Command to run Flask
    if sys.platform.startswith('win'):
        flask_cmd = ['python', 'run.py']
    else:
        flask_cmd = ['python3', 'run.py']
    
    # Start Flask as a subprocess
    server_process = subprocess.Popen(
        flask_cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    # Print Flask output in real-time
    def print_output(stream):
        for line in iter(stream.readline, ''):
            print(line, end='')
    
    # Start threads to print output
    threading.Thread(target=print_output, args=(server_process.stdout,), daemon=True).start()
    threading.Thread(target=print_output, args=(server_process.stderr,), daemon=True).start()
    
    return server_process

def is_server_running():
    """Check if the server is running"""
    import http.client
    try:
        # Всегда проверяем на 127.0.0.1 (localhost), даже если сервер запущен на 0.0.0.0
        conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=1)
        conn.request("HEAD", "/")
        response = conn.getresponse()
        conn.close()
        return response.status < 400
    except Exception as e:
        print(f"Error checking server status: {str(e)}")
        return False

def open_browser():
    """Open the browser to the landing page"""
    print(f"Opening {landing_url} in your default browser...")
    webbrowser.open(landing_url)

def handle_exit(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, handle_exit)
    
    # Start the Flask server
    server_process = start_flask_server()
    
    # Wait for the server to start
    print("Waiting for server to start...")
    max_attempts = 30
    attempts = 0
    while not is_server_running() and attempts < max_attempts:
        time.sleep(1)
        attempts += 1
        if attempts % 5 == 0:
            print(f"Still waiting for server... ({attempts}/{max_attempts})")
    
    if attempts >= max_attempts:
        print("Error: Server did not start in the expected time.")
        server_process.terminate()
        sys.exit(1)
    
    print("Server is up and running!")
    
    # Open browser after a short delay to ensure server is fully initialized
    time.sleep(2)
    open_browser()
    
    print("\n" + "="*50)
    print(f"Crypto Payment System is running at {server_url}")
    print(f"Landing page: {landing_url}")
    print(f"Admin Console: {server_url}/admin")
    print("="*50)
    print("\nPress Ctrl+C to stop the server.")
    
    try:
        # Keep the script running until Ctrl+C
        server_process.wait()
    except KeyboardInterrupt:
        server_process.terminate()
        print("\nServer stopped. Goodbye!") 