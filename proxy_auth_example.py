#!/usr/bin/env python3
import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def create_chrome_driver_with_proxy_auth():
    """
    Chrome tarayıcıyı açıp proxy kimlik doğrulama eklentisini kullanarak döndürür.
    """
    # Chrome seçeneklerini ayarla
    chrome_options = Options()
    
    # Headless modu (opsiyonel)
    # chrome_options.add_argument("--headless")
    
    # Tarayıcı boyutu ve diğer ayarlar
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-extensions")
    
    # Yerel proxy_auth_plugin dizininden eklentiyi ekle
    # Not: Tam yolu kullanın veya göreceli yolu doğru şekilde belirtin
    plugin_file = os.path.abspath('proxy_auth_plugin/proxy_auth_plugin.zip')
    if os.path.exists(plugin_file):
        print(f"Eklenti bulundu: {plugin_file}")
        chrome_options.add_extension(plugin_file)
    else:
        print(f"HATA: Eklenti bulunamadı: {plugin_file}")
        print(f"Mevcut dizin: {os.getcwd()}")
        # Alternatif olarak doğrudan proxy ayarı (eklenti olmadan)
        print("Alternatif proxy ayarları kullanılıyor...")
        proxy_line = get_random_proxy()
        if proxy_line:
            parts = proxy_line.strip().split(':')
            if len(parts) == 4:
                ip, port, username, password = parts
                proxy_formatted = f"{username}:{password}@{ip}:{port}"
                chrome_options.add_argument(f'--proxy-server=http://{ip}:{port}')
                # Not: Bu durumda kimlik doğrulama için ek bir yöntem gerekir
    
    # WebDriver'ı başlat
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def get_random_proxy():
    """
    proxies.txt dosyasından rastgele bir proxy satırı döndürür.
    """
    try:
        with open('proxies.txt', 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
            if proxies:
                return random.choice(proxies)
    except Exception as e:
        print(f"Proxy dosyasını okuma hatası: {e}")
    return None

def main():
    """
    Ana fonksiyon - Proxy kimlik doğrulama eklentisini kullanarak siteyi ziyaret eder.
    """
    driver = None
    try:
        print("Chrome tarayıcı başlatılıyor...")
        driver = create_chrome_driver_with_proxy_auth()
        
        print("Hedef siteye gidiliyor...")
        driver.get("https://httpbin.org/ip")  # IP adresini kontrol etmek için
        time.sleep(3)
        
        # IP bilgisini görüntüle
        page_source = driver.page_source
        print(f"Sayfa kaynağı: {page_source}")
        
        print("Siteyi yükleme başarılı!")
        # Biraz bekle ki sonucu görebilelim
        time.sleep(5)
        
    except Exception as e:
        print(f"Hata oluştu: {e}")
    finally:
        if driver:
            print("Tarayıcı kapatılıyor...")
            driver.quit()

if __name__ == "__main__":
    main() 