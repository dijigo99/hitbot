#!/usr/bin/env python3
import os
import sys
import time
import random
import requests
import datetime
from urllib.parse import urlparse

def log_message(msg):
    """Basit loglama fonksiyonu"""
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def simulate_scroll():
    """Sayfa kaydırma davranışını simüle eder"""
    scroll_count = random.randint(5, 15)
    log_message(f"{scroll_count} kaydırma hareketi simüle ediliyor...")
    for i in range(scroll_count):
        time.sleep(random.uniform(1.0, 3.5))
        if i % 3 == 0:
            log_message("Sayfa kaydırıldı")

def simulate_click():
    """Sayfa üzerinde tıklama davranışını simüle eder"""
    click_count = random.randint(2, 5)
    log_message(f"{click_count} tıklama hareketi simüle ediliyor...")
    for i in range(click_count):
        time.sleep(random.uniform(2.0, 5.0))
        log_message("Sayfa üzerinde bir bağlantıya tıklandı")

def main():
    """Ana test fonksiyonu"""
    TARGET_URL = '101firsat.com'
    REQUEST_COUNT = 10
    VISIT_DURATION_MIN = 30
    VISIT_DURATION_MAX = 120
    
    print("-" * 50)
    print(f"101firsat.com Gerçekçi Ziyaret Testi")
    print(f"Ziyaret sayısı: {REQUEST_COUNT}")
    print(f"Her ziyarette sitede kalma süresi: {VISIT_DURATION_MIN}-{VISIT_DURATION_MAX} saniye")
    print("-" * 50)
    
    # Kullanıcı agent'larını tanımla
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/113.0.5672.121 Mobile/15E148 Safari/604.1"
    ]
    
    # Referrer (Yönlendiren) URL'leri
    referrers = [
        "https://www.google.com/",
        "https://www.instagram.com/",
        "https://www.facebook.com/",
        "https://twitter.com/",
        None  # Doğrudan ziyaret
    ]
    
    # Hedef URL'yi düzgün formata getir
    if not TARGET_URL.startswith(('http://', 'https://')):
        TARGET_URL = f"https://{TARGET_URL}"
    
    successful_visits = 0
    
    # Ziyaretleri gerçekleştir
    for i in range(REQUEST_COUNT):
        log_message(f"Ziyaret #{i+1}/{REQUEST_COUNT} başlatılıyor...")
        
        # Her ziyaret için random UA ve referrer seç
        user_agent = random.choice(user_agents)
        referrer = random.choice(referrers)
        
        # Kullanıcı profil ve referrer tipi bilgisini logla
        ua_type = "Mobil" if "Mobile" in user_agent or "iPhone" in user_agent else "Masaüstü"
        browser_type = "Chrome" if "Chrome" in user_agent else "Firefox" if "Firefox" in user_agent else "Safari" if "Safari" in user_agent else "Diğer"
        
        ref_type = "Doğrudan" if referrer is None else "Google" if "google" in referrer else "Sosyal Medya"
        
        log_message(f"Kullanıcı profili: {ua_type} - {browser_type}")
        log_message(f"Referrer tipi: {ref_type}")
        
        # Oturum oluştur
        session = requests.Session()
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1'  # Do Not Track
        })
        
        if referrer:
            session.headers.update({'Referer': referrer})
        
        try:
            # Ana sayfayı ziyaret et
            log_message(f"Ana sayfa ziyaret ediliyor: {TARGET_URL}")
            start_time = time.time()
            response = session.get(TARGET_URL, timeout=20, verify=False)
            
            if response.status_code == 200:
                log_message(f"✅ Ana sayfa başarıyla yüklendi (HTTP {response.status_code})")
                
                # Sitede geçirilecek rastgele süreyi belirle
                site_duration = random.randint(VISIT_DURATION_MIN, VISIT_DURATION_MAX)
                log_message(f"Sitede {site_duration} saniye geçirilecek...")
                
                # Kullanıcı davranışlarını simüle et
                remaining_time = site_duration
                while remaining_time > 0:
                    # Sayfayı kaydır
                    if remaining_time > 10:
                        simulate_scroll()
                        elapsed = random.randint(5, 10)
                        remaining_time -= elapsed
                        log_message(f"Kalan süre: {remaining_time} saniye")
                    
                    # İç sayfayı ziyaret et (simüle)
                    if remaining_time > 15:
                        simulate_click()
                        elapsed = random.randint(10, 15)
                        remaining_time -= elapsed
                        log_message(f"Kalan süre: {remaining_time} saniye")
                    
                    # Son süreyi tüket
                    if remaining_time > 0:
                        log_message(f"Son {remaining_time} saniye bekleniyor...")
                        time.sleep(remaining_time)
                        remaining_time = 0
                
                total_duration = time.time() - start_time
                log_message(f"✅ Ziyaret tamamlandı! Süre: {total_duration:.2f} saniye")
                successful_visits += 1
            else:
                log_message(f"❌ Ziyaret başarısız: HTTP {response.status_code}")
        
        except Exception as e:
            log_message(f"❌ Ziyaret sırasında hata: {e}")
        
        if i < REQUEST_COUNT - 1:
            # Sonraki ziyaret için bekle (3-8 saniye)
            wait_time = random.uniform(3, 8)
            log_message(f"Sonraki ziyaret için {wait_time:.1f} saniye bekleniyor...")
            time.sleep(wait_time)
    
    # Sonuç özeti
    success_rate = (successful_visits / REQUEST_COUNT) * 100
    log_message(f"Test tamamlandı: {successful_visits}/{REQUEST_COUNT} başarılı ziyaret ({success_rate:.1f}%)")
    
    return successful_visits

if __name__ == "__main__":
    main() 