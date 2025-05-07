#!/usr/bin/env python3
import os
import sys
import time
import datetime

# App.py dosyasını import etmeden önce gerekli ortam değişkenlerini ayarla
os.environ['TARGET_URL'] = '101firsat.com'
os.environ['REQUEST_COUNT'] = '10'
os.environ['TIMEOUT'] = '20'
os.environ['USE_DIRECT_CONNECTION'] = 'true'
os.environ['MAX_PROXY_RETRIES'] = '3'
os.environ['SEARCH_DELAY'] = '3'
os.environ['REQUEST_DELAY'] = '6'
os.environ['RANDOMIZE_DELAYS'] = 'true'
os.environ['SIMULATE_USER_BEHAVIOR'] = 'true'

# Kullanıcı Davranışı Ayarları
os.environ['MIN_TIME_ON_SITE'] = '30'
os.environ['MAX_TIME_ON_SITE'] = '120'
os.environ['WEIGHT_DIRECT_CLICK'] = '80'  # Doğrudan ziyaret ağırlığı
os.environ['WEIGHT_GOOGLE_REFERRAL'] = '10'
os.environ['WEIGHT_EXTERNAL_LINK'] = '10'
os.environ['EXTERNAL_REFERRERS'] = 'instagram.com,facebook.com,twitter.com'

# Kullanıcı Profil Ayarları
os.environ['USE_RANDOM_PROFILE'] = 'true'
os.environ['DEFAULT_PROFILE'] = 'chrome_windows'

print("Test başlatılıyor: 101firsat.com")
print(f"Başlangıç zamanı: {datetime.datetime.now()}")
print("Yapılandırılan Ayarlar:")
print("----------------------")
print(f"Hedef URL: 101firsat.com")
print(f"İstek Sayısı: 10")
print(f"Doğrudan Bağlantı: Açık")
print(f"Kullanıcı Davranış Simülasyonu: Açık")
print(f"Sitede Geçirilecek Süre: 30-120 saniye")
print(f"Ziyaret Tipi: Doğrudan Ziyaret (%80), Google Araması (%10), Harici Referans (%10)")
print("----------------------")

try:
    # Önce mevcut dizindeki app.py modülünden run_test fonksiyonunu import et
    from app import run_test
    
    # Test ayarlarını oluştur
    settings = {
        'target_url': '101firsat.com',
        'request_count': 10,
        'timeout': 20,
        'use_direct_connection': True,
        'max_proxy_retries': 3,
        'search_delay': 3,
        'request_delay': 6,
        'randomize_delays': True,
        'simulate_user_behavior': True
    }
    
    # Testi çalıştır
    successful_requests = run_test(settings)
    
    print(f"Test tamamlandı: {successful_requests}/10 başarılı istek")
    print(f"Bitiş zamanı: {datetime.datetime.now()}")
    
except Exception as e:
    print(f"Test sırasında hata oluştu: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

sys.exit(0) 