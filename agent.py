from flask import Flask, jsonify, request, send_from_directory
import os
import platform
import psutil
import requests
from datetime import datetime, timedelta
from flask_cors import CORS
from flask_socketio import SocketIO, emit
# from socketio import AsyncClient
import asyncio
import threading
import argparse

from urllib.parse import unquote

# parser = argparse.ArgumentParser(description="Agent server for remote file management and system information")
# parser.add_argument('-i', '--ip', type=str, help='Master server IP address')
# parser.add_argument('-p', '--port', type=int, help='Master server port number')
# parser.add_argument('-name', '--name', type=str, help='Agent name')

# args = parser.parse_args()

# ip_address = args.ip
# port_number = args.port
# agent_name = args.name

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
# sio = AsyncClient()

BASE_DIR = f'/home/{os.getlogin()}' if platform.system() == 'Linux' else os.path.expanduser("~")

# Caching variables
cached_public_ip = None
last_ip_fetch_time = None
IP_CACHE_DURATION = timedelta(minutes=1)  

def list_files(directory):
    files = []
    print(directory)
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            files.append({'name': filename, 'type': 'file'})
        elif os.path.isdir(file_path):
            files.append({'name': filename + '/', 'type': 'directory'})
    return files

def get_file_content(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

@app.route('/')
def file_explorer():
    path = request.args.get('path', '')
    full_path = os.path.join(BASE_DIR, path) if platform.system() == 'Linux' else BASE_DIR + path
    print(full_path)
    if not os.path.exists(full_path):
        return jsonify({'error': f'Path does not exist: {path}'}), 404

    files = list_files(full_path)
    return jsonify({'files': files, 'current_path': path})

@app.route('/upload', methods=['POST'])
def upload_file():
    path = request.form['path']
    upload_dir = os.path.join(BASE_DIR, path)

    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            filename = os.path.join(upload_dir, file.filename)
            file.save(filename)
            return jsonify({'message': 'File uploaded successfully'}), 200

    return jsonify({'error': 'No file uploaded'}), 400

@app.route('/delete', methods=['POST'])
def delete_file():
    data = request.get_json()
    path = data.get('path')
    filename = data.get('filename')
    file_path = os.path.join(BASE_DIR, path, filename)

    if os.path.exists(file_path):
        if os.path.isdir(file_path):
            os.rmdir(file_path)
        else:
            os.remove(file_path)
        return jsonify({'message': 'File deleted successfully'}), 200
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/rename', methods=['POST'])
def rename_file():
    data = request.get_json()
    path = data.get('path', '')
    old_name = data.get('old_name', '')
    new_name = data.get('new_name', '')

    old_path = os.path.join(BASE_DIR, path, old_name)
    new_path = os.path.join(BASE_DIR, path, new_name)

    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        return jsonify({'message': 'File renamed successfully'}), 200
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/create_file', methods=['POST'])
def create_file():
    data = request.get_json()
    path = data.get('path')
    file_name = data.get('file_name')
    file_content = data.get('file_content')
    file_path = os.path.join(BASE_DIR, path, file_name)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        return jsonify({'message': 'File created successfully'}), 200
    except Exception as err:
        return jsonify({'error': str(err)}), 500


@app.route('/get_content', methods=['POST'])
def get_file_content_api():
    print(request.json)  
    data = request.get_json()
    path = data.get('path')
    filename = data.get('filename')
    file_path = os.path.join(BASE_DIR, path, filename)

    if os.path.exists(file_path):
        content = get_file_content(file_path)
        return jsonify({'content': content}), 200
    else:
        return jsonify({'error': 'File not found'}), 404


@app.route('/download/<path:file_path>', methods=['GET'])
def download_file(file_path):
    try:
        decoded_file_path = unquote(file_path)

        absolute_file_path = os.path.normpath(os.path.join(BASE_DIR, decoded_file_path))
        # print(absolute_file_path)
        if not absolute_file_path.startswith(BASE_DIR):
            return jsonify({'error': 'Invalid file path or unauthorized access'}), 403

        if not os.path.isfile(absolute_file_path):
            return jsonify({'error': 'File not found or invalid path'}), 404

        # print(decoded_file_path.split(BASE_DIR)[0],decoded_file_path.split(BASE_DIR)[1])
        return send_from_directory(os.path.dirname(absolute_file_path), os.path.basename(absolute_file_path), as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# def get_public_ip():
#     global cached_public_ip, last_ip_fetch_time

#     current_time = datetime.now()

#     if cached_public_ip is None or last_ip_fetch_time is None or (current_time - last_ip_fetch_time) > IP_CACHE_DURATION:
#         try:
#             response = requests.get('https://ipinfo.io/ip')
#             cached_public_ip = response.text.strip()
#             last_ip_fetch_time = current_time
#         except requests.RequestException as e:
#             print(f"Error getting public IP: {e}")
#             return None

#     return cached_public_ip

# def get_size(bytes, suffix="B"):
#     factor = 1024
#     for unit in ["", "K", "M", "G", "T", "P"]:
#         if bytes < factor:
#             return f"{bytes:.2f}{unit}{suffix}"
#         bytes /= factor

# def get_system_info():
#     system_info = {}

#     uname = platform.uname()
#     system_info['System'] = uname.system
#     system_info['NodeName'] = uname.node
#     system_info['Release'] = uname.release
#     system_info['Version'] = uname.version
#     system_info['Machine'] = uname.machine
#     system_info['Processor'] = uname.processor
    
#     boot_time_timestamp = psutil.boot_time()
#     bt = datetime.fromtimestamp(boot_time_timestamp)
#     system_info['BootTime'] = f"{bt.year}/{bt.month}/{bt.day} {bt.hour}:{bt.minute}:{bt.second}"
    
#     system_info['PhysicalCores'] = psutil.cpu_count(logical=False)
#     system_info['TotalCores'] = psutil.cpu_count(logical=True)
#     cpufreq = psutil.cpu_freq()
#     system_info['MaxFrequency'] = f"{cpufreq.max:.2f}Mhz"
#     system_info['MinFrequency'] = f"{cpufreq.min:.2f}Mhz"
#     system_info['CurrentFrequency'] = f"{cpufreq.current:.2f}Mhz"
    
#     system_info['TotalCPUUsage'] = f"{psutil.cpu_percent(interval=1)}%"  
    
#     memory_info = {}
#     svmem = psutil.virtual_memory()
#     memory_info['Total'] = get_size(svmem.total)
#     memory_info['Available'] = get_size(svmem.available)
#     memory_info['Used'] = get_size(svmem.used)
#     memory_info['Percentage'] = f"{svmem.percent}%"
#     system_info['MemoryInformation'] = memory_info
    
#     swap_info = {}
#     swap = psutil.swap_memory()
#     swap_info['Total'] = get_size(swap.total)
#     swap_info['Free'] = get_size(swap.free)
#     swap_info['Used'] = get_size(swap.used)
#     swap_info['Percentage'] = f"{swap.percent}%"
#     system_info['Swap'] = swap_info

#     system_info['PublicIP'] = get_public_ip()

#     return system_info

# @app.route('/system_info', methods=['GET'])
# def system_info():
#     return jsonify(get_system_info())


# @sio.event
# async def connect():
#     print("Connected to the master server")
#     await sio.emit('get_system_info_from_agent', {
#         "public_ip": get_public_ip(),
#         "name": agent_name
#     })

# @sio.event
# async def disconnect():
#     print("Disconnected from the master server")
#     await sio.emit('agent_disconnected', {
#         "public_ip": get_public_ip(),
#         "name": agent_name
#     })

# async def start_socketio_client():
#     try:
#         await sio.connect(f'http://{ip_address}:{port_number}')
#         await sio.wait()  # connection is alive 
#     except Exception as e:
#         print(f"Failed to connect to master server: {e}")

# def run_socketio_client():
#     asyncio.run(start_socketio_client())

if __name__ == '__main__':
    # client_thread = threading.Thread(target=run_socketio_client)
    # client_thread.daemon = True 
    # client_thread.start()

    socketio.run(app, debug=True, host="0.0.0.0", port=3000)