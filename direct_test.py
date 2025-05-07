#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
İstek sonuçlarını doğrudan göstermek için özel bir test script'i
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import time
import os
import threading
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# İstek sonuç verilerini tutacak global değişken
request_results = []

@app.route('/')
def index():
    return render_template('test_results.html')

@app.route('/api/results', methods=['GET'])
def get_results():
    return jsonify(request_results)

@app.route('/api/clear', methods=['GET'])
def clear_results():
    global request_results
    request_results = []
    return jsonify({"success": True, "message": "Sonuçlar temizlendi"})

@app.route('/api/test', methods=['GET'])
def start_test():
    count = int(request.args.get('count', 5))
    thread = threading.Thread(target=generate_test_results, args=(count,))
    thread.daemon = True
    thread.start()
    return jsonify({"success": True, "message": f"{count} test sonucu üretiliyor"})

def generate_test_results(count):
    global request_results
    
    print(f"Başlatılıyor: {count} test sonucu üretiliyor")
    
    # Başlamadan önce sonuçları temizle
    request_results = []
    
    # Web arayüzünü güncelle
    socketio.emit('test_started', {'count': count})
    
    # Test sonuçları üret
    for i in range(1, count + 1):
        # Rastgele başarı/başarısızlık durumu
        success = random.choice([True, False])
        
        # Örnek sonuç verisi
        result = {
            'request_number': i,
            'total_requests': count,
            'success': success,
            'status_code': 200 if success else random.choice([404, 500, 502, 503]),
            'search_result': f"https://example.com/result-{i}" if success else None,
            'error': None if success else f"Test error #{i}",
            'keyword': f"test-keyword-{i}",
            'proxy': f"test-proxy-{i}" if not random.choice([True, False]) else None,
            'time_taken': random.uniform(0.5, 3.0)
        }
        
        # Sonuçları kaydet
        request_results.append(result)
        
        # Socket.IO ile gönder
        print(f"Sonuç #{i} gönderiliyor: {'Başarılı' if success else 'Başarısız'}")
        socketio.emit('request_result', result)
        
        # Yeni sonuç üretmeden önce bekle
        time.sleep(1)
    
    # Test tamamlandı bildirimi gönder
    success_count = sum(1 for r in request_results if r['success'])
    completion_data = {
        'total_requests': count,
        'successful_requests': success_count,
        'failed_requests': count - success_count,
        'success_rate': (success_count / count) * 100 if count > 0 else 0
    }
    
    print(f"Test tamamlandı: {success_count}/{count} başarılı")
    socketio.emit('test_completed', completion_data)

@socketio.on('connect')
def handle_connect():
    print(f"Client bağlandı: {request.sid}")
    socketio.emit('server_message', {'message': 'Bağlantı başarılı!'})

if __name__ == '__main__':
    # Test sonuçları sayfası için template klasörünü kontrol et
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    if not os.path.exists(os.path.join(template_dir, 'test_results.html')):
        os.makedirs(template_dir, exist_ok=True)
        with open(os.path.join(template_dir, 'test_results.html'), 'w', encoding='utf-8') as f:
            f.write('''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Sonuçları</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        #logs { height: 200px; overflow-y: auto; background-color: #222; color: #f8f8f8; font-family: monospace; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
        #results-container { height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 5px; }
        .request-result { margin-bottom: 15px; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .success { background-color: #d4edda; border-left: 5px solid #28a745; }
        .failure { background-color: #f8d7da; border-left: 5px solid #dc3545; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">Test Sonuçları</h1>
        
        <div class="row mb-3">
            <div class="col">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>Kontrol Paneli</span>
                    </div>
                    <div class="card-body">
                        <div class="mb-3">
                            <label for="requestCount" class="form-label">İstek Sayısı</label>
                            <input type="number" class="form-control" id="requestCount" min="1" max="20" value="5">
                        </div>
                        <button id="startTestBtn" class="btn btn-primary me-2">Test Başlat</button>
                        <button id="clearResultsBtn" class="btn btn-secondary">Sonuçları Temizle</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-5">
                <div class="card">
                    <div class="card-header">
                        Log
                    </div>
                    <div class="card-body">
                        <div id="logs"></div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-7">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>İstek Sonuçları</span>
                        <div id="progressStats" class="text-white"></div>
                    </div>
                    <div class="card-body">
                        <div class="progress mb-3" id="progressBar" style="display: none;">
                            <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
                        </div>
                        <div id="results-container">
                            <p class="text-muted text-center mt-5">Henüz sonuç yok. "Test Başlat" düğmesine tıklayın.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const logsElement = document.getElementById('logs');
            const resultsContainer = document.getElementById('results-container');
            const startTestBtn = document.getElementById('startTestBtn');
            const clearResultsBtn = document.getElementById('clearResultsBtn');
            const requestCount = document.getElementById('requestCount');
            const progressBar = document.getElementById('progressBar');
            const progressStats = document.getElementById('progressStats');
            
            // Log to page
            function log(message, color = '#f8f8f8') {
                const logLine = document.createElement('div');
                logLine.innerHTML = `<span style="color: ${color}">${new Date().toLocaleTimeString()} - ${message}</span>`;
                logsElement.appendChild(logLine);
                logsElement.scrollTop = logsElement.scrollHeight;
                console.log(`${new Date().toLocaleTimeString()} - ${message}`);
            }
            
            log('Sayfa yüklendi', '#8cffa0');
            
            // Socket.io connection
            let socket;
            try {
                socket = io();
                log('Socket.io bağlantısı kurulmaya çalışılıyor...', '#ffcc8c');
                
                socket.on('connect', function() {
                    log('Socket.io bağlantısı başarılı! Socket ID: ' + socket.id, '#8cffa0');
                });
                
                socket.on('disconnect', function(reason) {
                    log('Socket.io bağlantısı koptu. Sebep: ' + reason, '#ffcc8c');
                });
                
                socket.on('server_message', function(data) {
                    log('Sunucu mesajı: ' + data.message, '#8cffa0');
                });
                
                // Test started
                socket.on('test_started', function(data) {
                    log('Test başlatıldı: ' + data.count + ' istek', '#8cffa0');
                    progressBar.style.display = 'flex';
                    progressBar.querySelector('.progress-bar').style.width = '0%';
                    progressBar.querySelector('.progress-bar').setAttribute('aria-valuenow', 0);
                    progressStats.innerHTML = '<span class="badge bg-primary">Başlatılıyor...</span>';
                    
                    // Reset results container
                    resultsContainer.innerHTML = '';
                });
                
                // Individual request result
                socket.on('request_result', function(data) {
                    log('İstek sonucu alındı: #' + data.request_number, '#8cffa0');
                    console.log('Request result data:', data);
                    
                    // Create result element
                    const resultDiv = document.createElement('div');
                    resultDiv.className = 'request-result ' + (data.success ? 'success' : 'failure');
                    
                    // Set content
                    resultDiv.innerHTML = `
                        <div class="d-flex justify-content-between">
                            <h5>İstek #${data.request_number}</h5>
                            <span class="badge ${data.success ? 'bg-success' : 'bg-danger'}">${data.success ? 'Başarılı' : 'Başarısız'}</span>
                        </div>
                        <div><strong>Anahtar Kelime:</strong> ${data.keyword || 'Belirtilmedi'}</div>
                        <div><strong>Arama Sonucu:</strong> ${data.search_result || 'Bulunamadı'}</div>
                        <div><strong>Proxy:</strong> ${data.proxy || 'Doğrudan Bağlantı'}</div>
                        <div><strong>Durum Kodu:</strong> ${data.status_code || 'N/A'}</div>
                        <div><strong>İşlem Süresi:</strong> ${data.time_taken ? data.time_taken.toFixed(2) + ' saniye' : 'N/A'}</div>
                    `;
                    
                    // Add to container
                    resultsContainer.appendChild(resultDiv);
                    resultsContainer.scrollTop = resultsContainer.scrollHeight;
                    
                    // Update progress
                    const percent = (data.request_number / data.total_requests) * 100;
                    progressBar.querySelector('.progress-bar').style.width = `${percent}%`;
                    progressBar.querySelector('.progress-bar').setAttribute('aria-valuenow', percent);
                    progressStats.innerHTML = `<span class="badge bg-info">${data.request_number}/${data.total_requests}</span>`;
                });
                
                // Test completed
                socket.on('test_completed', function(data) {
                    log(`Test tamamlandı! ${data.successful_requests}/${data.total_requests} başarılı, Başarı oranı: ${data.success_rate.toFixed(2)}%`, '#8cffa0');
                    
                    // Reset progress
                    progressStats.innerHTML = `<span class="badge bg-success">Tamamlandı</span>`;
                    
                    // Show summary
                    const summaryDiv = document.createElement('div');
                    summaryDiv.className = 'alert alert-info mt-3';
                    summaryDiv.innerHTML = `
                        <h5>Test Tamamlandı</h5>
                        <div><strong>Başarılı İstekler:</strong> ${data.successful_requests}/${data.total_requests}</div>
                        <div><strong>Başarı Oranı:</strong> ${data.success_rate.toFixed(2)}%</div>
                    `;
                    resultsContainer.appendChild(summaryDiv);
                    resultsContainer.scrollTop = resultsContainer.scrollHeight;
                });
                
            } catch (e) {
                log('Socket.io başlatma hatası: ' + e.message, '#ff8c8c');
                console.error('Socket.io başlatma hatası:', e);
            }
            
            // Start test button
            startTestBtn.addEventListener('click', function() {
                const count = parseInt(requestCount.value);
                log('Test başlatılıyor: ' + count + ' istek', '#ffcc8c');
                
                // Send API request to start test
                fetch('/api/test?count=' + count)
                    .then(response => response.json())
                    .then(data => {
                        log('API yanıtı: ' + data.message, '#8cffa0');
                    })
                    .catch(error => {
                        log('API hatası: ' + error.message, '#ff8c8c');
                    });
            });
            
            // Clear results button
            clearResultsBtn.addEventListener('click', function() {
                log('Sonuçlar temizleniyor...', '#ffcc8c');
                
                // Send API request to clear results
                fetch('/api/clear')
                    .then(response => response.json())
                    .then(data => {
                        log('API yanıtı: ' + data.message, '#8cffa0');
                        resultsContainer.innerHTML = '<p class="text-muted text-center mt-5">Henüz sonuç yok. "Test Başlat" düğmesine tıklayın.</p>';
                        progressBar.style.display = 'none';
                        progressStats.innerHTML = '';
                    })
                    .catch(error => {
                        log('API hatası: ' + error.message, '#ff8c8c');
                    });
            });
        });
    </script>
</body>
</html>''')
    
    print("Test sonuçları görüntüleme uygulaması başlatılıyor...")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True) 