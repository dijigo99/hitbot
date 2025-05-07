#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Socket.IO bağlantısını test etmek için basit bir uygulama
"""

from flask import Flask, render_template
from flask_socketio import SocketIO
import time
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('socket_test.html')

@socketio.on('connect')
def handle_connect():
    print("Client connected!")
    socketio.emit('server_message', {'message': 'Bağlantı başarılı!'})

@socketio.on('test_message')
def handle_test_message(data):
    print(f"Received test message: {data}")
    socketio.emit('server_response', {'response': f"Mesajınız alındı: {data.get('message', 'Boş mesaj')}"})

def send_dummy_results():
    """Send dummy results every 3 seconds"""
    count = 1
    while True:
        socketio.emit('request_result', {
            'request_number': count,
            'total_requests': 5,
            'proxy': f"test-proxy-{count}",
            'success': count % 2 == 0,  # Alternate success/failure
            'status_code': 200 if count % 2 == 0 else 404,
            'search_result': f"https://example.com/result-{count}" if count % 2 == 0 else None,
            'error': None if count % 2 == 0 else "Test error message",
            'keyword': f"test-keyword-{count}",
            'time_taken': 1.5
        })
        print(f"Dummy result #{count} sent")
        
        count += 1
        if count > 5:
            break
        time.sleep(3)

@socketio.on('start_test')
def handle_start_test(data):
    print("Starting dummy test...")
    # Start dummy results thread
    threading.Thread(target=send_dummy_results, daemon=True).start()
    return {'status': 'Test started'}

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 