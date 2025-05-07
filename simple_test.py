#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Çok basit Socket.IO test uygulaması
"""

from flask import Flask, render_template
from flask_socketio import SocketIO
import time
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Test</title>
        <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    </head>
    <body>
        <h1>Simple Test</h1>
        <button id="testButton">Send Test</button>
        <div id="output" style="margin-top: 20px; padding: 10px; border: 1px solid #ccc; min-height: 200px;"></div>
        
        <script>
            const output = document.getElementById('output');
            const testButton = document.getElementById('testButton');
            
            // Log to page
            function log(msg) {
                const div = document.createElement('div');
                div.textContent = new Date().toLocaleTimeString() + ': ' + msg;
                output.appendChild(div);
                console.log(msg);
            }
            
            log('Page loaded');
            
            // Connect to Socket.IO
            const socket = io();
            
            socket.on('connect', () => {
                log('Connected to server - socket ID: ' + socket.id);
            });
            
            socket.on('disconnect', (reason) => {
                log('Disconnected: ' + reason);
            });
            
            socket.on('test_response', (data) => {
                log('Test response received: ' + JSON.stringify(data));
            });
            
            // Send test on button click
            testButton.addEventListener('click', () => {
                log('Sending test message');
                socket.emit('test_message', {data: 'Test at ' + new Date().toISOString()});
            });
            
            // Auto test
            setTimeout(() => {
                log('Auto test starting');
                socket.emit('auto_test');
            }, 1000);
        </script>
    </body>
    </html>
    """

@socketio.on('connect')
def handle_connect():
    print("Client connected!")
    socketio.emit('test_response', {'message': 'Bağlantı başarılı!', 'time': time.time()})

@socketio.on('test_message')
def handle_test_message(data):
    print(f"Test message received: {data}")
    socketio.emit('test_response', {'message': 'Mesaj alındı', 'data': data, 'time': time.time()})

@socketio.on('auto_test')
def handle_auto_test():
    print("Auto test requested")
    
    def send_test_messages():
        for i in range(1, 4):
            print(f"Sending test message {i}")
            socketio.emit('test_response', {
                'message': f'Test message {i}',
                'count': i,
                'time': time.time()
            })
            time.sleep(2)
    
    # Start test in background
    thread = threading.Thread(target=send_test_messages)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    print("Starting simple Socket.IO test server on port 5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 