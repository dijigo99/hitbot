#!/usr/bin/env python3
import os
import sys
import time
import random
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def log_message(msg):
    """Basit loglama fonksiyonu"""
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def simulate_scroll(driver, min_scrolls=5, max_scrolls=15):
    """Sayfa kaydırma davranışını simüle eder"""
    scroll_count = random.randint(min_scrolls, max_scrolls)
    log_message(f"{scroll_count} kaydırma hareketi simüle ediliyor...")
    
    for i in range(scroll_count):
        # Rastgele bir mesafe kaydır (200-800px)
        scroll_amount = random.randint(200, 800)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        
        # Kaydırma sonrası kısa bekleme (gerçekçi davranış için)
        time.sleep(random.uniform(1.0, 3.5))
        
        if i % 3 == 0:
            log_message("Sayfa kaydırıldı")

def click_random_links(driver, min_clicks=2, max_clicks=5):
    """Sayfadaki rastgele linklere tıklama davranışını simüle eder"""
    try:
        # Tüm linkleri bul
        links = driver.find_elements(By.TAG_NAME, "a")
        
        # Sadece aynı domain içindeki linkleri filtrele
        current_domain = driver.current_url.split('/')[2]  # domain.com şeklinde alır
        internal_links = []
        
        for link in links:
            href = link.get_attribute('href')
            if href and current_domain in href and link.is_displayed() and link.is_enabled():
                internal_links.append(link)
        
        if not internal_links:
            log_message("Tıklanabilir iç link bulunamadı.")
            return
        
        # Rastgele sayıda link seç ve tıkla
        click_count = min(random.randint(min_clicks, max_clicks), len(internal_links))
        log_message(f"{click_count} tıklama hareketi simüle ediliyor...")
        
        for i in range(click_count):
            # Rastgele bir link seç
            link = random.choice(internal_links)
            internal_links.remove(link)  # Aynı linke tekrar tıklamamak için
            
            log_message(f"Tıklanıyor: {link.text[:30]}..." if link.text else "Tıklanıyor: [isimsiz link]")
            
            # JavaScript ile tıklama (daha güvenilir)
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", link)
            time.sleep(random.uniform(1.0, 2.0))  # Scroll sonrası kısa bekleme
            
            # Yeni sekme/sayfa açılmasını önlemek için try/except kullanıyoruz
            try:
                current_window = driver.current_window_handle
                driver.execute_script("arguments[0].click();", link)
                
                # Yeni sekme açıldı mı kontrol et
                if len(driver.window_handles) > 1:
                    # Ana pencereye geri dön
                    driver.switch_to.window(current_window)
                
                # Sayfa yüklenme süresi için bekle
                time.sleep(random.uniform(3.0, 5.0))
                
                # Rastgele biraz kaydır
                driver.execute_script(f"window.scrollBy(0, {random.randint(100, 400)});")
                time.sleep(random.uniform(2.0, 4.0))
                
                # Ana sayfaya geri dön
                driver.back()
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                log_message(f"Link tıklama hatası: {e}")
                # Hata olursa ana sayfaya dön
                try:
                    driver.get(driver.current_url)
                    time.sleep(2)
                except:
                    pass
    
    except Exception as e:
        log_message(f"Tıklama simülasyonu hatası: {e}")

def main():
    """Ana test fonksiyonu"""
    TARGET_URL = 'https://101firsat.com'
    REQUEST_COUNT = 5  # Daha az ziyaret - daha güvenilir
    VISIT_DURATION_MIN = 30
    VISIT_DURATION_MAX = 120
    
    print("-" * 50)
    print(f"101firsat.com Gerçekçi Ziyaret Testi (Selenium)")
    print(f"Ziyaret sayısı: {REQUEST_COUNT}")
    print(f"Her ziyarette sitede kalma süresi: {VISIT_DURATION_MIN}-{VISIT_DURATION_MAX} saniye")
    print("-" * 50)
    
    # Referrer (Yönlendiren) URL'leri
    referrers = [
        "https://www.google.com/search?q=101firsat",
        "https://www.instagram.com/",
        "https://www.facebook.com/",
        "https://twitter.com/",
        None  # Doğrudan ziyaret
    ]
    
    successful_visits = 0
    
    # Ziyaretleri gerçekleştir
    for i in range(REQUEST_COUNT):
        log_message(f"Ziyaret #{i+1}/{REQUEST_COUNT} başlatılıyor...")
        
        # Referrer seç
        referrer = random.choice(referrers)
        ref_type = "Doğrudan" if referrer is None else "Google" if "google" in referrer else "Sosyal Medya"
        log_message(f"Referrer tipi: {ref_type}")
        
        # Chrome seçeneklerini yapılandır
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Headless mod (gerekirse açın)
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        
        # UA seçme (rastgele masaüstü/mobil)
        is_mobile = random.choice([True, False, False])  # %33 mobil
        
        if is_mobile:
            # Mobil kullanıcı simülasyonu
            mobile_agents = [
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/113.0.5672.121 Mobile/15E148 Safari/604.1",
                "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
            ]
            user_agent = random.choice(mobile_agents)
            chrome_options.add_argument(f"user-agent={user_agent}")
            chrome_options.add_argument("--window-size=375,812")  # iPhone X boyutu
            device_type = "Mobil"
        else:
            # Masaüstü kullanıcı simülasyonu
            desktop_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"
            ]
            user_agent = random.choice(desktop_agents)
            chrome_options.add_argument(f"user-agent={user_agent}")
            device_type = "Masaüstü"
        
        # Tarayıcı tipini belirle
        browser_type = "Chrome" if "Chrome" in user_agent else "Firefox" if "Firefox" in user_agent else "Safari" if "Safari" in user_agent else "Diğer"
        
        log_message(f"Kullanıcı profili: {device_type} - {browser_type}")
        
        # Referrer ekle
        if referrer:
            chrome_options.add_argument(f"--referer={referrer}")
        
        # WebDriver başlat
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Sitede geçirilecek süreyi belirle
            site_duration = random.randint(VISIT_DURATION_MIN, VISIT_DURATION_MAX)
            
            # Ana sayfayı ziyaret et
            log_message(f"Ana sayfa ziyaret ediliyor: {TARGET_URL}")
            driver.get(TARGET_URL)
            
            # Sayfa yüklenmesini bekle
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            log_message(f"✅ Ana sayfa başarıyla yüklendi, başlık: {driver.title}")
            log_message(f"Sitede {site_duration} saniye geçirilecek...")
            
            # Kullanıcı davranışlarını simüle et
            remaining_time = site_duration
            start_time = time.time()
            
            # Birkaç saniye bekle (sayfa incelemesi)
            initial_wait = random.uniform(2.0, 5.0)
            time.sleep(initial_wait)
            remaining_time -= initial_wait
            
            # Davranış döngüsü
            while remaining_time > 0:
                current_time = time.time() - start_time
                if current_time >= site_duration:
                    break
                    
                remaining_time = site_duration - current_time
                log_message(f"Kalan süre: {remaining_time:.1f} saniye")
                
                # Sayfayı kaydır
                if remaining_time > 15:
                    simulate_scroll(driver)
                    time.sleep(random.uniform(1.0, 3.0))
                
                # Sayfa içi linklere tıkla
                if remaining_time > 30:
                    click_random_links(driver)
                    # İç sayfa gezintisi için biraz daha zaman ayır
                    time.sleep(random.uniform(2.0, 5.0))
                
                # Biraz daha bekle
                if remaining_time > 0:
                    wait_time = min(remaining_time, random.uniform(3.0, 8.0))
                    time.sleep(wait_time)
                    remaining_time -= wait_time
            
            total_duration = time.time() - start_time
            log_message(f"✅ Ziyaret tamamlandı! Süre: {total_duration:.2f} saniye")
            successful_visits += 1
            
        except Exception as e:
            log_message(f"❌ Ziyaret sırasında hata: {e}")
        
        finally:
            # WebDriver'ı kapat
            try:
                driver.quit()
            except:
                pass
        
        if i < REQUEST_COUNT - 1:
            # Sonraki ziyaret için bekle (15-30 saniye)
            wait_time = random.uniform(15, 30)
            log_message(f"Sonraki ziyaret için {wait_time:.1f} saniye bekleniyor...")
            time.sleep(wait_time)
    
    # Sonuç özeti
    success_rate = (successful_visits / REQUEST_COUNT) * 100
    log_message(f"Test tamamlandı: {successful_visits}/{REQUEST_COUNT} başarılı ziyaret ({success_rate:.1f}%)")
    
    return successful_visits

if __name__ == "__main__":
    main() 