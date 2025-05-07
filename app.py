#!/usr/bin/env python3
import json
import random
import time
import os
import sys
import threading
import concurrent.futures
from urllib.parse import quote, urlparse
from queue import Queue
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException, Timeout, ProxyError
from bs4 import BeautifulSoup
import re

# Modülleri import ediyoruz
from google_search import GoogleSearch
from behavior import UserBehavior, ClickType
from profiles import UserProfile
from analytics import Analytics
from cookie_checker import CookieChecker
from scheduler import HitScheduler

# Initialize Flask and SocketIO
app = Flask(__name__)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # CORS izinlerini açıyoruz
    async_mode='eventlet',     # eventlet kullanarak asenkron modu ayarlıyoruz
    logger=True,               # Socket.IO günlüklerini etkinleştiriyoruz
    engineio_logger=True,      # Engine.IO günlüklerini etkinleştiriyoruz
    ping_timeout=120,          # Ping zaman aşımını uzatıyoruz (60'tan 120'ye)
    ping_interval=15           # Ping aralığını kısaltıyoruz (25'ten 15'e)
)

# Load environment variables
try:
    load_dotenv()
    print("Environment variables loaded from .env file")
except Exception as e:
    print(f"Could not load .env file: {e}")
    print("Using default environment variables")

# Global variables
stop_event = threading.Event()
test_thread = None
TARGET_URL = os.getenv('TARGET_URL', '')
REQUEST_COUNT = int(os.getenv('REQUEST_COUNT', 5))
TIMEOUT = int(os.getenv('TIMEOUT', 10))
USE_DIRECT_CONNECTION = os.getenv('USE_DIRECT_CONNECTION', 'false').lower() == 'true'
MAX_PROXY_RETRIES = int(os.getenv('MAX_PROXY_RETRIES', 3))
SEARCH_DELAY = float(os.getenv('SEARCH_DELAY', 2))
REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', 3))
RANDOMIZE_DELAYS = os.getenv('RANDOMIZE_DELAYS', 'true').lower() == 'true'
SIMULATE_USER_BEHAVIOR = os.getenv('SIMULATE_USER_BEHAVIOR', 'true').lower() == 'true'
DEFAULT_KEYWORDS = ["web sitesi", "blog", "hizmetler", "ürünler"]

# Modülleri başlatıyoruz
def log_message(message, color=None):
    socketio.emit('log_message', {'message': message, 'color': color})
    print(message)  # Also print to console for debugging

# Modül örnekleri oluşturuyoruz
google_search = GoogleSearch(logger_func=log_message)
user_behavior = UserBehavior(logger_func=log_message)
user_profile = UserProfile(logger_func=log_message)
analytics = Analytics(logger_func=log_message)
cookie_checker = CookieChecker(logger_func=log_message)
scheduler = HitScheduler(run_func=None, logger_func=log_message)  # run_func will be set later

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """When a client connects to the server, send initial data"""
    try:
        # Send initial configuration to client
        socketio.emit('init_data', {
            'target_url': TARGET_URL,
            'request_count': REQUEST_COUNT,
            'timeout': TIMEOUT,
            'use_direct_connection': USE_DIRECT_CONNECTION,
            'max_proxy_retries': MAX_PROXY_RETRIES,
            'search_delay': SEARCH_DELAY,
            'request_delay': REQUEST_DELAY,
            'randomize_delays': RANDOMIZE_DELAYS,
            'simulate_user_behavior': SIMULATE_USER_BEHAVIOR
        })
        log_message("Kullanıcı arayüzü bağlandı")
        
        # Send cookie status to client
        try:
            cookie_status = cookie_checker.get_cookie_summary()
            socketio.emit('cookie_status', cookie_status)
        except Exception as e:
            log_message(f"Cookie bilgisi gönderilirken hata: {e}", "#ffcc8c")
        
        # Send scheduler status
        try:
            schedule_times = scheduler.get_schedule()
            next_run = scheduler.get_next_run_time()
            socketio.emit('scheduler_status', {
                'schedule_times': schedule_times,
                'next_run': next_run,
                'is_running': scheduler.running
            })
        except Exception as e:
            log_message(f"Zamanlayıcı bilgisi gönderilirken hata: {e}", "#ffcc8c")
            
    except Exception as e:
        log_message(f"Bağlantı sırasında beklenmeyen hata: {e}", "#ff8c8c")
        print(f"Bağlantı hatası: {e}")

def load_cookies():
    """Load cookies from cookies.json file"""
    return cookie_checker.load_cookies()

def save_cookies(cookies):
    """Save cookies to cookies.json file"""
    return cookie_checker.save_cookies(cookies)

def load_proxies():
    """Load proxies from proxies.txt and webshareproxies.txt files"""
    proxies = []
    
    # Önce normal proxies.txt dosyasını kontrol edelim
    try:
        with open('proxies.txt', 'r') as f:
            standard_proxies = [line.strip() for line in f if line.strip()]
            log_message(f"{len(standard_proxies)} adet proxy yüklendi (proxies.txt)", "#8cffa0")
            proxies.extend(standard_proxies)
    except FileNotFoundError:
        log_message("proxies.txt bulunamadı, webshare proxyleri kontrol ediliyor", "#ffcc8c")
    
    # Webshare proxies'i kontrol edelim
    try:
        with open('webshareproxies.txt', 'r') as f:
            webshare_proxies = [line.strip() for line in f if line.strip()]
            log_message(f"{len(webshare_proxies)} adet Webshare proxy yüklendi (webshareproxies.txt)", "#8cffa0")
            proxies.extend(webshare_proxies)
    except FileNotFoundError:
        log_message("webshareproxies.txt bulunamadı", "#ffcc8c")
    
    if not proxies:
        log_message("Hiç proxy bulunamadı! Lütfen proxy ekleyin veya 'Doğrudan Bağlantı' ayarını aktifleştirin.", "#ff8c8c")
    else:
        log_message(f"Toplam {len(proxies)} adet proxy yüklendi", "#8cffa0")
    
    return proxies

def save_proxies(proxies):
    """Save proxies to proxies.txt file"""
    try:
        with open('proxies.txt', 'w') as f:
            for proxy in proxies:
                f.write(f"{proxy}\n")
        return True
    except Exception as e:
        log_message(f"Proxy kaydetme hatası: {e}", "#ff8c8c")
        return False

def load_user_agents():
    """Load user agents from user_agents.txt file"""
    try:
        with open('user_agents.txt', 'r') as f:
            user_agents = [line.strip() for line in f if line.strip()]
            log_message(f"{len(user_agents)} adet user agent yüklendi", "#8cffa0")
            if user_agents:
                return user_agents
    except FileNotFoundError as e:
        log_message(f"User agent yükleme hatası: {e}", "#ff8c8c")
    
    # Default User-Agent
    default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    log_message("Varsayılan user agent kullanılıyor", "#ffcc8c")
    return [default_ua]

def load_keywords():
    """Load keywords from keywords.txt file"""
    try:
        with open('keywords.txt', 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
            if keywords:
                log_message(f"{len(keywords)} adet anahtar kelime yüklendi", "#8cffa0")
                return keywords
            else:
                log_message("keywords.txt boş, varsayılan anahtar kelimeler kullanılıyor", "#ffcc8c")
                return DEFAULT_KEYWORDS
    except FileNotFoundError:
        log_message("keywords.txt bulunamadı, varsayılan anahtar kelimeler kullanılıyor", "#ffcc8c")
        return DEFAULT_KEYWORDS

def save_keywords(keywords):
    """Save keywords to keywords.txt file"""
    try:
        with open('keywords.txt', 'w', encoding='utf-8') as f:
            for keyword in keywords:
                f.write(f"{keyword}\n")
        return True
    except Exception as e:
        log_message(f"Anahtar kelime kaydetme hatası: {e}", "#ff8c8c")
        return False

def test_proxy(proxy, timeout=5):
    """Test if a proxy is working"""
    try:
        # Webshare formatını kontrol et (IP:PORT:USERNAME:PASSWORD)
        parts = proxy.split(':')
        
        if len(parts) == 4:  # Webshare formatı (IP:PORT:USERNAME:PASSWORD)
            ip, port, username, password = parts
            formatted_proxy = f"http://{username}:{password}@{ip}:{port}"
        elif proxy.startswith('http://') or proxy.startswith('https://'):
            formatted_proxy = proxy
        elif proxy.startswith('socks4://') or proxy.startswith('socks5://'):
            formatted_proxy = proxy
        else:
            # Standart IP:PORT formatı - HTTP proxy olarak varsay
            formatted_proxy = f"http://{proxy}"
        
        proxies = {
            'http': formatted_proxy,
            'https': formatted_proxy
        }
        
        # Use a simple test URL
        response = requests.get('http://httpbin.org/ip', 
                               proxies=proxies, 
                               timeout=timeout,
                               verify=False)
        return response.status_code == 200
    except Exception as e:
        print(f"Proxy test hatası: {e}")
        return False

def get_working_proxies(proxy_list, max_workers=5):
    """Test proxies in parallel and return working ones"""
    working_proxies = []
    
    if not proxy_list:
        return working_proxies
    
    log_message(f"{len(proxy_list)} proxy test ediliyor...")
    socketio.emit('proxy_test_started', {'count': len(proxy_list)})
    
    # Proxy testlerini daha güvenilir yapmak için thread sayısını azaltalım
    max_workers = min(max_workers, 5)  # En fazla 5 paralel istek
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_proxy = {executor.submit(test_proxy, proxy): proxy for proxy in proxy_list}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_proxy)):
            proxy = future_to_proxy[future]
            try:
                is_working = future.result()
                if is_working:
                    working_proxies.append(proxy)
                    
                    # Kullanıcı dostu proxy gösterimi
                    if len(proxy.split(':')) == 4:  # Webshare formatı
                        ip, port, username, _ = proxy.split(':')
                        display_proxy = f"{ip}:{port} (Webshare)"
                    else:
                        display_proxy = proxy
                        
                    log_message(f"✓ Çalışan proxy bulundu: {display_proxy}", "#8cffa0")
                    socketio.emit('proxy_test_result', {'proxy': proxy, 'working': True})
                else:
                    # Kullanıcı dostu proxy gösterimi
                    if len(proxy.split(':')) == 4:  # Webshare formatı
                        ip, port, username, _ = proxy.split(':')
                        display_proxy = f"{ip}:{port} (Webshare)"
                    else:
                        display_proxy = proxy
                        
                    log_message(f"✕ Çalışmayan proxy: {display_proxy}", "#ff8c8c")
                    socketio.emit('proxy_test_result', {'proxy': proxy, 'working': False})
            except Exception as e:
                # Kullanıcı dostu proxy gösterimi
                if len(proxy.split(':')) == 4:  # Webshare formatı
                    ip, port, username, _ = proxy.split(':')
                    display_proxy = f"{ip}:{port} (Webshare)"
                else:
                    display_proxy = proxy
                    
                log_message(f"Proxy test hatası {display_proxy}: {e}", "#ff8c8c")
                socketio.emit('proxy_test_result', {'proxy': proxy, 'working': False})
            
            # Emit progress every 3 proxies
            if (i+1) % 3 == 0 or i+1 == len(proxy_list):
                log_message(f"{i+1}/{len(proxy_list)} proxy test edildi. {len(working_proxies)} proxy çalışıyor.")
                
    socketio.emit('proxy_test_completed', {
        'working_count': len(working_proxies),
        'total_count': len(proxy_list)
    })
    
    log_message(f"Proxy testi tamamlandı. {len(working_proxies)}/{len(proxy_list)} proxy çalışıyor.")
    return working_proxies

def create_session(proxy, user_agent, cookies):
    """Create a session with the given proxy, user agent, and cookies"""
    session = requests.Session()
    
    # Kullanıcı davranışı simüle et
    click_type = user_behavior.get_random_click_type()
    session, click_type = user_behavior.apply_behavior_to_session(session, click_type)
    
    # Kullanıcı profili uygula
    session = user_profile.apply_profile_to_session(session)
    
    # Configure proxy if not using direct connection
    if proxy and not USE_DIRECT_CONNECTION:
        try:
            # Webshare formatını kontrol et (IP:PORT:USERNAME:PASSWORD)
            parts = proxy.split(':')
            
            if len(parts) == 4:  # Webshare formatı (IP:PORT:USERNAME:PASSWORD)
                ip, port, username, password = parts
                formatted_proxy = f"http://{username}:{password}@{ip}:{port}"
                log_message(f"Webshare proxy formatı algılandı ve dönüştürüldü", "#8cffa0")
                session.proxies = {
                    'http': formatted_proxy,
                    'https': formatted_proxy
                }
            elif proxy.startswith('http://') or proxy.startswith('https://'):
                session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
            elif proxy.startswith('socks4://') or proxy.startswith('socks5://'):
                session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
            else:
                # Standart IP:PORT formatı - HTTP proxy olarak varsay
                formatted_proxy = f"http://{proxy}"
                session.proxies = {
                    'http': formatted_proxy,
                    'https': formatted_proxy
                }
                
            log_message(f"Proxy ayarlandı: {proxy.split('@')[-1] if '@' in proxy else proxy}", "#8cffa0")
        except Exception as e:
            log_message(f"Proxy kurulum hatası: {e}", "#ff8c8c")
    
    # Add cookies if not already set by the profile
    if not session.cookies and cookies:
        for key, value in cookies.items():
            if isinstance(value, dict) and 'value' in value:
                session.cookies.set(key, value['value'], domain='.google.com')
            else:
                session.cookies.set(key, value, domain='.google.com')
    
    return session

def get_delay(base_delay):
    """Get a randomized delay if RANDOMIZE_DELAYS is enabled"""
    if RANDOMIZE_DELAYS:
        # Randomize by ±30%
        variation = base_delay * 0.3
        return random.uniform(base_delay - variation, base_delay + variation)
    return base_delay

def simulate_google_search(session, keyword, site_domain):
    """Simulate a Google search and click the result link if found"""
    # Google Search modülünü kullanarak arama yapıyoruz
    return google_search.perform_search(session, keyword)

def make_request(proxy, user_agent, cookies, keywords, request_number, total_requests):
    """Make a request to the target URL via Google Search"""
    start_time = time.time()
    result = {
        'request_number': request_number,
        'total_requests': total_requests,
        'proxy': proxy,
        'success': False,
        'status_code': None,
        'search_result': None,
        'error': None,
        'keyword': None
    }
    
    try:
        # Log request start
        if len(proxy.split(':')) == 4:  # Webshare formatı
            ip, port, username, _ = proxy.split(':')
            displayed_proxy = f"{ip}:{port} (Webshare)"
        else:
            displayed_proxy = proxy
            
        log_message(f"İstek #{request_number}/{total_requests} başlatılıyor... Proxy: {displayed_proxy}", "#8cffa0")
        
        # Zamanlamadan önce insan davranışı gecikme uygula
        delay = user_behavior.wait_before_request()
        
        # Random keyword seç
        keyword = random.choice(keywords) if keywords else None
        result['keyword'] = keyword
        
        # Adjust target URL format if needed
        target_url = TARGET_URL
        target_domain = urlparse(target_url).netloc
        if not target_domain:
            target_domain = target_url.split('/')[0]
            target_url = f"https://{target_url}"
        
        # Kullanıcı profilini seçerek session oluştur
        session = create_session(proxy, user_agent, cookies)
        
        # Google araması yaparak hedef siteye gidiş
        try:
            success, found_url = google_search.perform_search(session, keyword)
            result['search_result'] = found_url
        except Exception as e:
            log_message(f"Google araması sırasında hata: {e}", "#ff8c8c")
            raise e
        
        if success:
            result['success'] = True
            
            # Sitede geçirilen süreyi simüle et
            time_on_site = user_behavior.simulate_time_on_site()
            
            # Kaydırma davranışını simüle et
            scroll_events = user_behavior.simulate_scroll_pattern()
            
            # Log site interaction
            log_message(f"→ Sitede {time_on_site:.2f} saniye geçirildi, {len(scroll_events)} kaydırma hareketi yapıldı", "#8cffa0")
            
            # Analitik verileri kaydet
            analytics.log_request({
                'target_url': found_url or target_url,
                'status_code': 200,
                'response_time': time.time() - start_time,
                'proxy': proxy,
                'user_agent': session.headers.get('User-Agent', ''),
                'profile': getattr(session, 'profile_name', 'unknown'),
                'cookies': dict(session.cookies),
                'success': True
            })
        else:
            # Doğrudan bağlantı modunda bir deneme daha yap
            if USE_DIRECT_CONNECTION:
                log_message("Google araması başarısız oldu, doğrudan ziyaret deneniyor...", "#ffcc8c")
                direct_success = google_search.direct_visit(session)
                if direct_success:
                    result['success'] = True
                    result['search_result'] = TARGET_URL
                    
                    # Sitede geçirilen süreyi simüle et
                    time_on_site = user_behavior.simulate_time_on_site()
                    
                    # Başarılı isteği kaydet
                    analytics.log_request({
                        'target_url': TARGET_URL,
                        'status_code': 200,
                        'response_time': time.time() - start_time,
                        'proxy': proxy,
                        'user_agent': session.headers.get('User-Agent', ''),
                        'profile': getattr(session, 'profile_name', 'unknown'),
                        'cookies': dict(session.cookies),
                        'success': True
                    })
                else:
                    result['error'] = "Doğrudan bağlantı başarısız oldu"
                    
                    # Başarısız isteği kaydet
                    analytics.log_request({
                        'target_url': TARGET_URL,
                        'status_code': None,
                        'response_time': time.time() - start_time,
                        'proxy': proxy,
                        'user_agent': session.headers.get('User-Agent', ''),
                        'profile': getattr(session, 'profile_name', 'unknown'),
                        'cookies': dict(session.cookies),
                        'success': False,
                        'error': result['error']
                    })
            else:
                result['error'] = "Google araması başarısız oldu"
                
                # Başarısız isteği kaydet
                analytics.log_request({
                    'target_url': TARGET_URL,
                    'status_code': None,
                    'response_time': time.time() - start_time,
                    'proxy': proxy,
                    'user_agent': session.headers.get('User-Agent', ''),
                    'profile': getattr(session, 'profile_name', 'unknown'),
                    'cookies': dict(session.cookies),
                    'success': False,
                    'error': result['error']
                })
    
    except Exception as e:
        result['error'] = str(e)
        log_message(f"İstek hatası: {e}", "#ff8c8c")
        
        # Başarısız isteği kaydet
        analytics.log_request({
            'target_url': TARGET_URL,
            'status_code': None,
            'response_time': time.time() - start_time,
            'proxy': proxy,
            'user_agent': user_agent,
            'profile': 'unknown',
            'cookies': cookies,
            'success': False,
            'error': str(e)
        })
    
    log_message(f"İstek #{request_number}/{total_requests} tamamlandı: {'✅ Başarılı' if result['success'] else '❌ Başarısız'}")
    result['time_taken'] = time.time() - start_time
    
    # Emit request result with debug log
    log_message(f"İstek sonucu socket üzerinden gönderiliyor (request_result olayı): İstek #{request_number}", "#8cffa0")
    
    try:
        # Simplify result data structure for debugging
        simple_result = {
            'request_number': request_number,
            'total_requests': total_requests,
            'success': result['success'],
            'status_code': result['status_code'],
            'keyword': result['keyword'],
            'proxy': str(proxy),
            'time_taken': result['time_taken'],
            'search_result': str(result['search_result'])
        }
        
        # Direct emit in main thread
        socketio.emit('request_result', simple_result)
        print(f"[DEBUG] Emitted request_result event for request #{request_number}")
    except Exception as e:
        print(f"[ERROR] Socket emit failed: {e}")
    
    return result

def make_request_with_retry(proxy_list, user_agent, cookies, keywords, request_number, total_requests):
    """Make a request with proxy retry mechanism"""
    if not proxy_list or USE_DIRECT_CONNECTION:
        # No proxies or direct connection mode, use None as proxy
        return make_request(None, user_agent, cookies, keywords, request_number, total_requests)
    
    # Try with different proxies up to MAX_PROXY_RETRIES
    for i in range(min(MAX_PROXY_RETRIES, len(proxy_list))):
        proxy = random.choice(proxy_list)
        log_message(f"İstek #{request_number}, Proxy Deneme #{i+1}/{MAX_PROXY_RETRIES}: {proxy}")
        
        result = make_request(proxy, user_agent, cookies, keywords, request_number, total_requests)
        if result['success']:
            return result
        
        log_message(f"Proxy başarısız oldu, yeni proxy deneniyor...", "#ffcc8c")
    
    log_message(f"Tüm proxy'ler başarısız oldu (istek #{request_number})", "#ff8c8c")
    return {
        'request_number': request_number,
        'total_requests': total_requests,
        'proxy': 'multiple_failed',
        'success': False,
        'status_code': None,
        'search_result': None,
        'error': "Tüm proxy'ler başarısız oldu",
        'keyword': None,
        'time_taken': 0
    }

def run_test(settings):
    """Run the test with the given settings"""
    global stop_event, TARGET_URL, REQUEST_COUNT, TIMEOUT, USE_DIRECT_CONNECTION, MAX_PROXY_RETRIES
    global SEARCH_DELAY, REQUEST_DELAY, RANDOMIZE_DELAYS, SIMULATE_USER_BEHAVIOR
    
    # Update settings from args if provided
    if 'target_url' in settings and settings['target_url']:
        TARGET_URL = settings['target_url']
    if 'request_count' in settings:
        REQUEST_COUNT = int(settings['request_count'])
    if 'timeout' in settings:
        TIMEOUT = int(settings['timeout'])
    if 'use_direct_connection' in settings:
        USE_DIRECT_CONNECTION = settings['use_direct_connection']
    if 'max_proxy_retries' in settings:
        MAX_PROXY_RETRIES = int(settings['max_proxy_retries'])
    if 'search_delay' in settings:
        SEARCH_DELAY = float(settings['search_delay'])
    if 'request_delay' in settings:
        REQUEST_DELAY = float(settings['request_delay'])
    if 'randomize_delays' in settings:
        RANDOMIZE_DELAYS = settings['randomize_delays']
    if 'simulate_user_behavior' in settings:
        SIMULATE_USER_BEHAVIOR = settings['simulate_user_behavior']
    
    # Set settings to GoogleSearch module
    google_search.target_url = TARGET_URL
    google_search.search_delay = SEARCH_DELAY
    google_search.randomize_delays = RANDOMIZE_DELAYS
    google_search.simulate_user_behavior = SIMULATE_USER_BEHAVIOR
    google_search.timeout = TIMEOUT
    
    # Reset stop event
    stop_event.clear()
    
    # Log test start
    log_message(f"Test başlatılıyor: {TARGET_URL}, İstek sayısı: {REQUEST_COUNT}")
    
    test_start_time = time.time()
    successful_requests = 0
    
    # Check if cookies are valid
    try:
        cookies_ok, missing_cookies, cookie_status = cookie_checker.check_cookies()
        if not cookies_ok:
            log_message(f"Uyarı: Cookie kontrol sorunu - {cookie_status}", "#ffcc8c")
    except Exception as e:
        log_message(f"Cookie kontrolü sırasında hata: {str(e)}", "#ffcc8c")
    
    # Load resources
    try:
        proxies = load_proxies()
        working_proxies = []
        
        if not USE_DIRECT_CONNECTION and proxies:
            # Test proxies only if needed
            working_proxies = get_working_proxies(proxies)
            if not working_proxies:
                log_message("Çalışan proxy bulunamadı. Doğrudan bağlantıya geçiliyor.", "#ffcc8c")
                USE_DIRECT_CONNECTION = True
        
        user_agents = load_user_agents()
        keywords = load_keywords()
        cookies = load_cookies()
        
        # Log resources
        log_message(f"Kullanılabilir proxy sayısı: {len(working_proxies)}")
        log_message(f"Kullanılabilir user agent sayısı: {len(user_agents)}")
        log_message(f"Kullanılabilir anahtar kelime sayısı: {len(keywords)}")
        log_message(f"Kullanılabilir cookie sayısı: {len(cookies)}")
    except Exception as e:
        log_message(f"Kaynaklar yüklenirken hata: {str(e)}", "#ff8c8c")
        # Yine de devam etmek için temel değerleri ayarla
        proxies = []
        working_proxies = []
        user_agents = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"]
        keywords = ["web sitesi"]
        cookies = {}
    
    try:
        # Make requests
        for i in range(REQUEST_COUNT):
            if stop_event.is_set():
                log_message("Test durduruldu", "#ffcc8c")
                break
            
            # Select a random user agent
            user_agent = random.choice(user_agents) if user_agents else None
            
            try:
                # Make the request with retry
                result = make_request_with_retry(working_proxies, user_agent, cookies, keywords, i+1, REQUEST_COUNT)
                
                if result['success']:
                    successful_requests += 1
            except Exception as e:
                log_message(f"İstek #{i+1} sırasında hata: {str(e)}", "#ff8c8c")
                continue
            
            # Add delay between requests
            if i < REQUEST_COUNT - 1 and not stop_event.is_set():
                try:
                    req_delay = user_behavior.get_random_click_type()
                    log_message(f"Sonraki istek için {req_delay:.2f} saniye bekleniyor...")
                    for _ in range(int(req_delay)):
                        if stop_event.is_set():
                            break
                        time.sleep(1)
                except Exception as e:
                    log_message(f"Bekleme sırasında hata: {str(e)}", "#ffcc8c")
                    time.sleep(3)  # Fallback delay
        
        # Calculate success rate
        success_rate = (successful_requests / REQUEST_COUNT) * 100 if REQUEST_COUNT > 0 else 0
        test_duration = time.time() - test_start_time
        
        # Log test completion
        log_message(f"Test tamamlandı! {successful_requests}/{REQUEST_COUNT} başarılı istek, Başarı oranı: {success_rate:.2f}%", "#8cffa0")
        
        # Record analytics
        try:
            analytics.log_summary({
                'test_duration': test_duration,
                'successful_requests': successful_requests,
                'failed_requests': REQUEST_COUNT - successful_requests,
                'success_rate': success_rate
            })
        except Exception as e:
            log_message(f"Analitik verisi kaydedilirken hata: {str(e)}", "#ffcc8c")
        
        # Notify frontend
        try:
            socketio.emit('test_completed', {
                'total_requests': REQUEST_COUNT,
                'successful_requests': successful_requests,
                'failed_requests': REQUEST_COUNT - successful_requests,
                'success_rate': success_rate
            })
            
            # Debug message
            print(f"[DEBUG] Test completed - emitted test_completed event: {successful_requests}/{REQUEST_COUNT} successful")
        except Exception as e:
            log_message(f"Sonuç gönderilirken hata: {str(e)}", "#ffcc8c")
            print(f"[ERROR] Failed to emit test completion: {e}")
    
    except Exception as e:
        error_msg = str(e)
        log_message(f"Test sırasında hata oluştu: {error_msg}", "#ff8c8c")
        
        try:
            socketio.emit('test_completed', {
                'total_requests': REQUEST_COUNT,
                'successful_requests': successful_requests,
                'failed_requests': REQUEST_COUNT - successful_requests,
                'success_rate': 0
            })
        except:
            print(f"[ERROR] Fatal error during test: {error_msg}")
    
    return successful_requests

# Scheduler için run_function tanımla
def run_scheduled_test(settings):
    """Run a scheduled test"""
    # Bu fonksiyon scheduler tarafından çağrılır
    log_message("⏰ Zamanlanmış test çalıştırılıyor...", "#8cffa0")
    
    # Settings değerlerini ayarla
    default_settings = {
        'target_url': TARGET_URL,
        'request_count': REQUEST_COUNT,
        'timeout': TIMEOUT,
        'use_direct_connection': USE_DIRECT_CONNECTION,
        'max_proxy_retries': MAX_PROXY_RETRIES,
        'search_delay': SEARCH_DELAY,
        'request_delay': REQUEST_DELAY,
        'randomize_delays': RANDOMIZE_DELAYS,
        'simulate_user_behavior': SIMULATE_USER_BEHAVIOR
    }
    
    # Settings'i güncelle
    if settings:
        default_settings.update(settings)
    
    # Test thread'i başlat
    def _run():
        run_test(default_settings)
    
    test_thread = threading.Thread(target=_run)
    test_thread.daemon = True
    test_thread.start()

# Scheduler'ı başlat
# Burada scheduler'ın run_func parametresini set ediyoruz
scheduler.run_func = run_scheduled_test

@socketio.on('start_test')
def handle_start_test(settings):
    """Handle start test event"""
    global test_thread, stop_event
    
    if test_thread and test_thread.is_alive():
        log_message("Test zaten çalışıyor", "#ffcc8c")
        return
    
    log_message("Test başlatılıyor...", "#8cffa0")
    
    # Start test in a separate thread
    stop_event.clear()
    test_thread = threading.Thread(target=run_test, args=(settings,))
    test_thread.daemon = True
    test_thread.start()

@socketio.on('stop_test')
def handle_stop_test():
    """Handle stop test event"""
    global stop_event
    
    log_message("Test durduruluyor...", "#ffcc8c")
    stop_event.set()

@socketio.on('get_proxies')
def handle_get_proxies():
    """Handle get proxies event"""
    proxies = load_proxies()
    socketio.emit('proxy_list', {'proxies': proxies})

@socketio.on('get_keywords')
def handle_get_keywords():
    """Handle get keywords event"""
    keywords = load_keywords()
    socketio.emit('keyword_list', {'keywords': keywords})

@socketio.on('add_proxy')
def handle_add_proxy(data):
    """Handle add proxy event"""
    proxy = data.get('proxy')
    if not proxy:
        log_message("Geçersiz proxy", "#ff8c8c")
        return
    
    proxies = load_proxies()
    if proxy not in proxies:
        proxies.append(proxy)
        save_proxies(proxies)
        log_message(f"Proxy eklendi: {proxy}", "#8cffa0")
    else:
        log_message(f"Proxy zaten listede: {proxy}", "#ffcc8c")

@socketio.on('remove_proxy')
def handle_remove_proxy(data):
    """Handle remove proxy event"""
    proxy = data.get('proxy')
    if not proxy:
        log_message("Geçersiz proxy", "#ff8c8c")
        return
    
    proxies = load_proxies()
    if proxy in proxies:
        proxies.remove(proxy)
        save_proxies(proxies)
        log_message(f"Proxy silindi: {proxy}", "#8cffa0")
    else:
        log_message(f"Proxy listede bulunamadı: {proxy}", "#ffcc8c")

@socketio.on('add_keyword')
def handle_add_keyword(data):
    """Handle add keyword event"""
    keyword = data.get('keyword')
    if not keyword:
        log_message("Geçersiz anahtar kelime", "#ff8c8c")
        return
    
    keywords = load_keywords()
    if keyword not in keywords:
        keywords.append(keyword)
        save_keywords(keywords)
        log_message(f"Anahtar kelime eklendi: {keyword}", "#8cffa0")
    else:
        log_message(f"Anahtar kelime zaten listede: {keyword}", "#ffcc8c")

@socketio.on('remove_keyword')
def handle_remove_keyword(data):
    """Handle remove keyword event"""
    keyword = data.get('keyword')
    if not keyword:
        log_message("Geçersiz anahtar kelime", "#ff8c8c")
        return
    
    keywords = load_keywords()
    if keyword in keywords:
        keywords.remove(keyword)
        save_keywords(keywords)
        log_message(f"Anahtar kelime silindi: {keyword}", "#8cffa0")
    else:
        log_message(f"Anahtar kelime listede bulunamadı: {keyword}", "#ffcc8c")

@socketio.on('get_cookies')
def handle_get_cookies():
    """Handle get cookies event"""
    cookies = load_cookies()
    socketio.emit('cookie_list', {'cookies': cookies})

@socketio.on('add_cookie')
def handle_add_cookie(data):
    """Handle add cookie event"""
    name = data.get('name')
    value = data.get('value')
    if not name or not value:
        log_message("Geçersiz cookie", "#ff8c8c")
        return
    
    cookies = load_cookies()
    cookies[name] = value
    save_cookies(cookies)
    log_message(f"Cookie eklendi: {name}", "#8cffa0")

@socketio.on('remove_cookie')
def handle_remove_cookie(data):
    """Handle remove cookie event"""
    name = data.get('name')
    if not name:
        log_message("Geçersiz cookie", "#ff8c8c")
        return
    
    cookies = load_cookies()
    if name in cookies:
        del cookies[name]
        save_cookies(cookies)
        log_message(f"Cookie silindi: {name}", "#8cffa0")
    else:
        log_message(f"Cookie bulunamadı: {name}", "#ffcc8c")

@socketio.on('import_cookies')
def handle_import_cookies(data):
    """Handle import cookies event"""
    cookies_data = data.get('cookies')
    if not cookies_data:
        log_message("Geçersiz cookie verisi", "#ff8c8c")
        return
    
    success, message = cookie_checker.import_cookies_from_json(json.dumps(cookies_data))
    log_message(message, "#8cffa0" if success else "#ff8c8c")
    
    # Send updated cookie list
    if success:
        cookies = load_cookies()
        socketio.emit('cookie_list', {'cookies': cookies})

# Zamanlayıcı (Scheduler) için yeni olay yöneticileri
@socketio.on('get_schedule')
def handle_get_schedule():
    """Handle get schedule event"""
    try:
        times = scheduler.get_schedule()
        next_run = scheduler.get_next_run_time()
        
        socketio.emit('schedule_list', {
            'times': times,
            'next_run': next_run,
            'is_running': scheduler.running
        })
        log_message("Zamanlanmış saatler gönderildi", "#8cffa0")
    except Exception as e:
        log_message(f"Zamanlanmış saatler gönderilirken hata: {e}", "#ff8c8c")
        print(f"Zamanlayıcı hatası: {e}")

@socketio.on('add_schedule_time')
def handle_add_schedule_time(data):
    """Handle add schedule time event"""
    time_str = data.get('time')
    if not time_str:
        log_message("Geçersiz zaman", "#ff8c8c")
        return
    
    success = scheduler.add_schedule_time(time_str)
    if success:
        log_message(f"Zamanlama eklendi: {time_str}", "#8cffa0")
    else:
        log_message(f"Zamanlama eklenemedi: {time_str}", "#ff8c8c")
    
    # Send updated schedule list
    handle_get_schedule()

@socketio.on('remove_schedule_time')
def handle_remove_schedule_time(data):
    """Handle remove schedule time event"""
    time_str = data.get('time')
    if not time_str:
        log_message("Geçersiz zaman", "#ff8c8c")
        return
    
    success = scheduler.remove_schedule_time(time_str)
    if success:
        log_message(f"Zamanlama silindi: {time_str}", "#8cffa0")
    else:
        log_message(f"Zamanlama silinemedi: {time_str}", "#ff8c8c")
    
    # Send updated schedule list
    handle_get_schedule()

@socketio.on('start_scheduler')
def handle_start_scheduler():
    """Handle start scheduler event"""
    if scheduler.running:
        log_message("Zamanlayıcı zaten çalışıyor", "#ffcc8c")
        return
    
    success = scheduler.start()
    if success:
        log_message("Zamanlayıcı başlatıldı", "#8cffa0")
    else:
        log_message("Zamanlayıcı başlatılamadı", "#ff8c8c")
    
    # Send updated schedule status
    handle_get_schedule()

@socketio.on('stop_scheduler')
def handle_stop_scheduler():
    """Handle stop scheduler event"""
    if not scheduler.running:
        log_message("Zamanlayıcı zaten durdurulmuş", "#ffcc8c")
        return
    
    success = scheduler.stop()
    if success:
        log_message("Zamanlayıcı durduruldu", "#8cffa0")
    else:
        log_message("Zamanlayıcı durdurulamadı", "#ff8c8c")
    
    # Send updated schedule status
    handle_get_schedule()

@socketio.on('run_now')
def handle_run_now():
    """Handle run now event"""
    success = scheduler.run_now()
    if success:
        log_message("Test şimdi başlatılıyor", "#8cffa0")
    else:
        log_message("Test başlatılamadı", "#ff8c8c")

# Profil yönetimi için olay işleyicileri
@socketio.on('get_profile_settings')
def handle_get_profile_settings():
    """Handle get profile settings event"""
    settings = {
        'use_random_profile': user_profile.use_random_profile,
        'default_profile': user_profile.default_profile
    }
    socketio.emit('profile_settings', settings)

@socketio.on('update_profile_settings')
def handle_update_profile_settings(data):
    """Handle update profile settings event"""
    if 'use_random_profile' in data:
        user_profile.use_random_profile = data['use_random_profile']
    
    if 'default_profile' in data:
        user_profile.default_profile = data['default_profile']
    
    # .env dosyasında da güncelle
    try:
        with open('.env', 'r') as f:
            env_content = f.read()
        
        env_content = re.sub(r'USE_RANDOM_PROFILE=.*', f'USE_RANDOM_PROFILE={str(user_profile.use_random_profile).lower()}', env_content)
        env_content = re.sub(r'DEFAULT_PROFILE=.*', f'DEFAULT_PROFILE={user_profile.default_profile}', env_content)
        
        with open('.env', 'w') as f:
            f.write(env_content)
    except Exception as e:
        log_message(f".env dosyası güncellenirken hata: {e}", "#ffcc8c")
        log_message("Bu normal bir durum olabilir, ayarlar geçici olarak kaydedildi.", "#ffcc8c")
    
    log_message("Profil ayarları güncellendi", "#8cffa0")

# Davranış ayarları için olay işleyicileri
@socketio.on('get_behavior_settings')
def handle_get_behavior_settings():
    """Handle get behavior settings event"""
    settings = {
        'min_time_on_site': user_behavior.min_time_on_site,
        'max_time_on_site': user_behavior.max_time_on_site,
        'weight_direct_click': user_behavior.click_type_weights[ClickType.DIRECT],
        'weight_google_referral': user_behavior.click_type_weights[ClickType.GOOGLE_REFERRAL],
        'weight_external_link': user_behavior.click_type_weights[ClickType.EXTERNAL_LINK],
        'external_referrers': user_behavior.external_referrers
    }
    socketio.emit('behavior_settings', settings)

@socketio.on('get_external_referrers')
def handle_get_external_referrers():
    """Handle get external referrers event"""
    try:
        socketio.emit('external_referrers', {'referrers': user_behavior.external_referrers})
        log_message("Harici referrerlar gönderildi", "#8cffa0")
    except Exception as e:
        log_message(f"Harici referrerlar gönderilirken hata: {e}", "#ff8c8c")
        print(f"Harici referrer hatası: {e}")

@socketio.on('save_behavior_settings')
def handle_save_behavior_settings(data):
    """Handle save behavior settings event"""
    try:
        # Değerleri güncelle
        if 'min_time_on_site' in data:
            user_behavior.min_time_on_site = float(data['min_time_on_site'])
        
        if 'max_time_on_site' in data:
            user_behavior.max_time_on_site = float(data['max_time_on_site'])
        
        # Tıklama tipi ağırlıklarını güncelle
        if 'weight_direct_click' in data:
            user_behavior.click_type_weights[ClickType.DIRECT] = int(data['weight_direct_click'])
        
        if 'weight_google_referral' in data:
            user_behavior.click_type_weights[ClickType.GOOGLE_REFERRAL] = int(data['weight_google_referral'])
        
        if 'weight_external_link' in data:
            user_behavior.click_type_weights[ClickType.EXTERNAL_LINK] = int(data['weight_external_link'])
        
        # .env dosyasında da güncelle
        try:
            with open('.env', 'r') as f:
                env_content = f.read()
            
            env_content = re.sub(r'MIN_TIME_ON_SITE=.*', f'MIN_TIME_ON_SITE={user_behavior.min_time_on_site}', env_content)
            env_content = re.sub(r'MAX_TIME_ON_SITE=.*', f'MAX_TIME_ON_SITE={user_behavior.max_time_on_site}', env_content)
            env_content = re.sub(r'WEIGHT_DIRECT_CLICK=.*', f'WEIGHT_DIRECT_CLICK={user_behavior.click_type_weights[ClickType.DIRECT]}', env_content)
            env_content = re.sub(r'WEIGHT_GOOGLE_REFERRAL=.*', f'WEIGHT_GOOGLE_REFERRAL={user_behavior.click_type_weights[ClickType.GOOGLE_REFERRAL]}', env_content)
            env_content = re.sub(r'WEIGHT_EXTERNAL_LINK=.*', f'WEIGHT_EXTERNAL_LINK={user_behavior.click_type_weights[ClickType.EXTERNAL_LINK]}', env_content)
            
            with open('.env', 'w') as f:
                f.write(env_content)
        except Exception as e:
            log_message(f".env dosyası güncellenirken hata: {e}", "#ffcc8c")
            log_message("Bu normal bir durum olabilir, ayarlar geçici olarak kaydedildi.", "#ffcc8c")
        
        log_message("Davranış ayarları güncellendi", "#8cffa0")
        
        # Güncellenmiş ayarları gönder
        handle_get_behavior_settings()
    except Exception as e:
        log_message(f"Davranış ayarları güncellenirken hata: {e}", "#ff8c8c")

@socketio.on('add_external_referrer')
def handle_add_external_referrer(data):
    """Handle add external referrer event"""
    referrer = data.get('referrer')
    if not referrer:
        log_message("Geçersiz referrer", "#ff8c8c")
        return
    
    if referrer not in user_behavior.external_referrers:
        user_behavior.external_referrers.append(referrer)
        
        # .env dosyasında da güncelle
        try:
            with open('.env', 'r') as f:
                env_content = f.read()
            
            # Mevcut EXTERNAL_REFERRERS değerini al veya oluştur
            referrers_str = ','.join(user_behavior.external_referrers)
            if 'EXTERNAL_REFERRERS=' in env_content:
                env_content = re.sub(r'EXTERNAL_REFERRERS=.*', f'EXTERNAL_REFERRERS={referrers_str}', env_content)
            else:
                env_content += f'\nEXTERNAL_REFERRERS={referrers_str}'
            
            with open('.env', 'w') as f:
                f.write(env_content)
        except Exception as e:
            log_message(f".env dosyası güncellenirken hata: {e}", "#ffcc8c")
            log_message("Bu normal bir durum olabilir, ayarlar geçici olarak kaydedildi.", "#ffcc8c")
        
        log_message(f"Referrer eklendi: {referrer}", "#8cffa0")
    else:
        log_message(f"Referrer zaten listede: {referrer}", "#ffcc8c")
    
    # Güncellenmiş listeyi gönder
    handle_get_behavior_settings()

@socketio.on('remove_external_referrer')
def handle_remove_external_referrer(data):
    """Handle remove external referrer event"""
    referrer = data.get('referrer')
    if not referrer:
        log_message("Geçersiz referrer", "#ff8c8c")
        return
    
    if referrer in user_behavior.external_referrers:
        user_behavior.external_referrers.remove(referrer)
        
        # .env dosyasında da güncelle
        try:
            with open('.env', 'r') as f:
                env_content = f.read()
            
            # Mevcut EXTERNAL_REFERRERS değerini güncelle
            referrers_str = ','.join(user_behavior.external_referrers)
            env_content = re.sub(r'EXTERNAL_REFERRERS=.*', f'EXTERNAL_REFERRERS={referrers_str}', env_content)
            
            with open('.env', 'w') as f:
                f.write(env_content)
        except Exception as e:
            log_message(f".env dosyası güncellenirken hata: {e}", "#ffcc8c")
            log_message("Bu normal bir durum olabilir, ayarlar geçici olarak kaydedildi.", "#ffcc8c")
        
        log_message(f"Referrer silindi: {referrer}", "#8cffa0")
    else:
        log_message(f"Referrer listede bulunamadı: {referrer}", "#ffcc8c")
    
    # Güncellenmiş listeyi gönder
    handle_get_behavior_settings()

# CORS ayarlarını ekleyelim
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Main entry point
if __name__ == '__main__':
    # Başlangıçta zamanlayıcıyı başlat (eğer program ilk kez çalışıyorsa)
    if os.getenv('START_SCHEDULER_ON_BOOT', 'false').lower() == 'true':
        scheduler.start()
        log_message("Zamanlayıcı otomatik olarak başlatıldı", "#8cffa0")
    
    # Uygulama ayarları
    port = int(os.getenv('PORT', 5000))
    
    # Render.com üzerinde çalışırken
    if os.getenv('RENDER', '') == 'true':
        # Render.com için eventlet kullanarak Socket.io'yu çalıştır
        socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False)
    else:
        # Geliştirme ortamı için normal başlatma
        socketio.run(app, host='0.0.0.0', port=port) 