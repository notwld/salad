from flask import Flask, jsonify, request, send_from_directory, render_template_string
import os
import platform
import psutil
import requests
from datetime import datetime, timedelta
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import shutil
from urllib.parse import unquote
import subprocess

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

BASE_DIR = f'/home/{os.getlogin()}' if platform.system() == 'Linux' else os.path.expanduser("~")

def list_files(directory):
    files = []
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                stats = os.stat(file_path)
                file_info = {
                    'name': filename,
                    'type': 'directory' if os.path.isdir(file_path) else 'file',
                    'size': stats.st_size,
                    'modified': datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                }
                if file_info['type'] == 'directory':
                    file_info['name'] += '/'
                files.append(file_info)
            except (PermissionError, OSError):
                continue
        return sorted(files, key=lambda x: (x['type'] == 'file', x['name'].lower()))
    except PermissionError:
        return []

@app.route('/')
def index():
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        template = f.read()
    return render_template_string(template)

@app.route('/api/files')
def list_directory():
    path = request.args.get('path', '')
    full_path = os.path.join(BASE_DIR, path) if platform.system() == 'Linux' else os.path.expanduser("~") + path
    print(full_path)
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return jsonify({'error': f'Path does not exist or is not a directory: {path}'}), 404

    if not full_path.startswith(BASE_DIR):
        return jsonify({'error': 'Access denied'}), 403

    files = list_files(full_path)
    return jsonify({
        'files': files,
        'current_path': path,
        'total_items': len(files)
    })
def run_code_serve_command(folder_path):
    """
    Run the 'code serve-web --port 8080' command in a specific directory,
    parse its output, and extract the IP address from the Web UI URL.
    """
    try:
        # Locate the 'code' executable
        code_path = shutil.which("code")
        if not code_path:
            raise FileNotFoundError("The 'code' command is not found. Ensure it is installed and in the system PATH.")

        # Change working directory
        os.chdir(folder_path)
        
        # Run the 'code serve-web' command
        result = subprocess.run(
            [code_path, "serve-web", "--port", "5050"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return {"success": True, "url": "http://127.0.0.1:5050"}

    except Exception as e:
        print(f"Error running 'code serve-web' command: {e}")
        return {"success": False, "error": str(e)}

@app.route('/api/vscode', methods=['POST'])
def open_vscode():
    data = request.get_json()
    path = data.get('path', '')
    path = os.path.join(BASE_DIR, path) if platform.system() == 'Linux' else os.path.expanduser("~") + path
    result = run_code_serve_command(path)
    return jsonify(result)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Coffee File Manager - A beautiful way to manage your files")
    parser.add_argument('-p', '--port', type=int, default=5000, help='Port number (default: 5000)')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host address (default: 127.0.0.1)')
    
    args = parser.parse_args()
    
    print(f"\n☕ Coffee File Manager is running!")
    print(f"📂 Base Directory: {BASE_DIR}")
    print(f"🌐 Access it at: http://{args.host}:{args.port}")
    print("\nPress Ctrl+C to quit\n")
    
    socketio.run(app, host=args.host, port=args.port, debug=True)