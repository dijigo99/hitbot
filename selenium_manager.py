#!/usr/bin/env python3
import os
import time
import random
import json
import threading
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class SeleniumManager:
    """Selenium tarayıcı yöneticisi sınıfı"""
    
    def __init__(self, logger_func=print, config_path="selenium_config.json"):
        """Selenium yöneticisini başlat."""
        self.logger = logger_func
        self.config_path = config_path
        self.config = self._load_config()
        self.running = False
        self.thread = None
        self.proxy_extension_path = os.path.join('proxy_auth_plugin', 'proxy_auth_plugin.zip')
        # Eklenti dizini yoksa oluştur
        if not os.path.exists('proxy_auth_plugin'):
            os.makedirs('proxy_auth_plugin')
        
    def _load_config(self):
        """Konfigürasyon dosyasından ayarları yükle."""
        default_config = {
            "use_selenium": False,
            "headless_mode": True,
            "min_time_on_site": 30,
            "max_time_on_site": 120,
            "use_proxy": False,
            "proxy_type": "random",
            "fixed_proxy": "",
            "device_type": "desktop"
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    return config
        except Exception as e:
            self.logger(f"Selenium ayarları yüklenirken hata: {e}", "#ff8c8c")
        
        return default_config
    
    def save_config(self, config):
        """Konfigürasyon ayarlarını kaydet."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f)
            self.config = config
            self.logger("Selenium ayarları kaydedildi.", "#8cffa0")
            return True
        except Exception as e:
            self.logger(f"Selenium ayarları kaydedilirken hata: {e}", "#ff8c8c")
            return False
    
    def get_config(self):
        """Mevcut konfigürasyon ayarlarını döndür."""
        return self.config
    
    def get_proxy(self, proxy_list):
        """Konfigürasyon ayarlarına göre proxy seç."""
        if not self.config.get("use_proxy", False):
            return None
            
        if not proxy_list:
            return None
            
        proxy_type = self.config.get("proxy_type", "random")
        
        if proxy_type == "fixed":
            return self.config.get("fixed_proxy", "")
        elif proxy_type == "round_robin":
            # Round robin implementasyonu için geliştirilecek
            return random.choice(proxy_list)
        else:  # random
            return random.choice(proxy_list)
    
    def prepare_proxy_extension(self, proxy_str):
        """Proxy Auth eklentisini hazırla ve zip dosyasını oluştur."""
        if not proxy_str or ':' not in proxy_str:
            return None
            
        try:
            # Eğer proxy string IP:PORT:USERNAME:PASSWORD formatındaysa parçala
            parts = proxy_str.split(':')
            if len(parts) < 4:
                self.logger(f"Geçersiz proxy formatı: {proxy_str}", "#ff8c8c")
                return None
                
            ip = parts[0]
            port = parts[1]
            username = parts[2]
            password = parts[3]
            
            # manifest.json dosyasını oluştur
            manifest_json = {
                "version": "1.0.0",
                "manifest_version": 2,
                "name": "Proxy Auth Plugin",
                "description": "Adds authenticated proxy support to Chrome for Selenium",
                "permissions": [
                    "proxy",
                    "tabs",
                    "webRequest",
                    "webRequestBlocking",
                    "<all_urls>"
                ],
                "background": {
                    "scripts": ["background.js"]
                },
                "browser_action": {
                    "default_icon": {
                        "16": "icon16.png",
                        "48": "icon48.png",
                        "128": "icon128.png"
                    }
                },
                "icons": {
                    "16": "icon16.png",
                    "48": "icon48.png",
                    "128": "icon128.png"
                }
            }
            
            # background.js dosyasını oluştur - spesifik proxy bilgileriyle
            background_js = f'''
            var config = {{
                mode: "fixed_servers",
                rules: {{
                    singleProxy: {{
                        scheme: "http",
                        host: "{ip}",
                        port: parseInt({port})
                    }},
                    bypassList: []
                }}
            }};

            chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

            function callbackFn(details) {{
                return {{
                    authCredentials: {{
                        username: "{username}",
                        password: "{password}"
                    }}
                }};
            }}

            chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {{urls: ["<all_urls>"]}},
                ['blocking']
            );
            '''
            
            # Proxy Auth Plugin dizini oluştur
            plugin_dir = 'proxy_auth_plugin'
            if not os.path.exists(plugin_dir):
                os.makedirs(plugin_dir)
                
            # manifest.json yaz
            with open(os.path.join(plugin_dir, 'manifest.json'), 'w') as f:
                json.dump(manifest_json, f)
                
            # background.js yaz
            with open(os.path.join(plugin_dir, 'background.js'), 'w') as f:
                f.write(background_js)
                
            # Basit ikonlar için içerikler (Base64 formatında)
            icon16 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAA4ElEQVQ4T7WTwQ2DMAxFbVEGYJC6QekG7QIVEi5wg0NP7QKdgG5AN2g3aJmgzgAlEjYywVKUQ3KL7O/n73wHaK1tOtO2KSHUUspWCCkeSil9tDHG1QnZP+sBIKdQ3SGrpay0VspmLIteA3IsFXwDQN6pDK9FUeyGYQhZv1CAkAIAkYrv++14t217sSwLcIyTSbCt/K/aLkbnHH6ZhCzLQm6bMQ5d152rqjp68KWUDQAc9kxwCMgwww/2nN/gFHAluTkAbIY4JISDtSdcGN5vJrGG59yD0zQdm6Z5MSGI4j/h5wvbj1fRDXWPJwAAAABJRU5ErkJggg=="
            icon48 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAA6UlEQVRoQ+2YzQ3DIAxGSVEGyCB1g3QDdoEKiQvcdOipXYBO0G7QbtBuUDJBnQFKJGzIj6UqPcS5oL7z57wHAhARBXaZmWfbSQjvAHBljD8xxgCAV8rV67qeUubq9y+lrxWldBFCLD7fOcA1YB3Qee+A/hRCCt+nEHLtk+i/A9Q4mkYd4qwZPeG+qc8ZK7lMqVQdoDuUy+21ruu+DMOwdl3328/8teTqOeDyQA0AIXX9CAB2mFxGKb1wzhe+dXKWUvqWPG+VTdPs2rZ9IyLnxlZKMkZEJyI6VlV1mOd5Zy/ZmwP2N5L/DvgBxCHCQX+NE58AAAAASUVORK5CYII="
            icon128 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAA+UlEQVR4Xu3UwQkAIAwEwdh/0VoJIhLYGZjrNruPmXnOPbeZcwvA+lQAAAYDUAB0//gEAMAAoADo/vEJAIABQAHQ/eMTAAADgAKg+8cnAAAGAAVA949PAAAMAAWBV8Vf4NtN38AAAQAGAAqA7h+fAAAYABQA3T8+AQAwACgAun98AgBgAFAAdP/4BADAAKAA6P7xCQCAAUAB0P3jEwAAA4ACoPvHJwAABgAFQPePTwAADACu8HL3Jj5vYALoJwAAdAAvANz9k08AACYAXgC4+yefAABMALwAcPdPPgEAmAB4AeDun3wCADAB8ALA3T/5BABgAuAFgLt/8gkAwATACwB3/+QXn1RiIWSUya0AAAAASUVORK5CYII="
            
            # Base64 içeriğini ikili dosyaya çevir
            import base64
            import re
            
            def save_base64_image(data_uri, file_path):
                # data:image/png;base64, kısmını kaldır
                if 'base64,' in data_uri:
                    header, encoded = data_uri.split('base64,', 1)
                else:
                    encoded = data_uri
                
                # Encoding kısmını al
                decoded_data = base64.b64decode(encoded)
                
                # Dosyaya yaz
                with open(file_path, 'wb') as f:
                    f.write(decoded_data)
            
            # İkon dosyalarını kaydet
            save_base64_image(icon16, os.path.join(plugin_dir, 'icon16.png'))
            save_base64_image(icon48, os.path.join(plugin_dir, 'icon48.png'))
            save_base64_image(icon128, os.path.join(plugin_dir, 'icon128.png'))
            
            # proxies.txt kopyala (gerekirse)
            if os.path.exists('proxies.txt'):
                import shutil
                shutil.copy2('proxies.txt', os.path.join(plugin_dir, 'proxies.txt'))
            
            # ZIP dosyası oluştur
            import zipfile
            
            zip_path = os.path.join(plugin_dir, 'proxy_auth_plugin.zip')
            zipf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
            
            # Dosyaları ekle
            for root, dirs, files in os.walk(plugin_dir):
                for file in files:
                    if file != 'proxy_auth_plugin.zip':  # ZIP dosyasının kendisini ekleme
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, plugin_dir)
                        zipf.write(file_path, arcname)
            
            zipf.close()
            
            self.logger(f"Proxy eklentisi oluşturuldu: {zip_path}", "#8cffa0")
            return zip_path
            
        except Exception as e:
            self.logger(f"Proxy eklentisi oluşturulurken hata: {e}", "#ff8c8c")
            return None
    
    def start_browser(self, url, proxy=None):
        """Tarayıcıyı başlat ve URL'e git."""
        try:
            chrome_options = Options()
            
            # Headless modu etkinleştir
            if self.config.get("headless_mode", True):
                chrome_options.add_argument("--headless")
                
            # Tarayıcı boyutu ve diğer ayarlar
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            
            # Extension'ları devre dışı bırakmayı kaldırdık, eklenti kullanacağız
            # chrome_options.add_argument("--disable-extensions")
            
            # Cihaz tipi seçimi
            device_type = self.config.get("device_type", "desktop")
            is_mobile = False
            
            if device_type == "mobile":
                is_mobile = True
            elif device_type == "mixed":
                is_mobile = random.choice([True, False])
                
            # UA ve ekran boyutunu ayarla
            if is_mobile:
                mobile_agents = [
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/113.0.5672.121 Mobile/15E148 Safari/604.1",
                    "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
                ]
                user_agent = random.choice(mobile_agents)
                chrome_options.add_argument(f"user-agent={user_agent}")
                chrome_options.add_argument("--window-size=375,812")  # iPhone X boyutu
                self.logger(f"Mobil kullanıcı ajanı: {user_agent}", "#8cffa0")
            else:
                desktop_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"
                ]
                user_agent = random.choice(desktop_agents)
                chrome_options.add_argument(f"user-agent={user_agent}")
                self.logger(f"Masaüstü kullanıcı ajanı: {user_agent}", "#8cffa0")
                
            # Proxy ayarları
            if proxy and self.config.get("use_proxy", False):
                # Proxy formatını kontrol et ve ayarla
                try:
                    # Eğer IP:PORT:USERNAME:PASSWORD formatındaysa eklenti kullan
                    if proxy.count(':') >= 3:
                        # Proxy Auth eklentisini oluştur
                        plugin_path = self.prepare_proxy_extension(proxy)
                        if plugin_path:
                            chrome_options.add_extension(plugin_path)
                            self.logger(f"Proxy Auth eklentisi yüklendi", "#8cffa0")
                        else:
                            self.logger(f"Proxy Auth eklentisi oluşturulamadı, doğrudan proxy kullanılacak", "#ffcc8c")
                            # Doğrudan bağlantıya düş
                            parts = proxy.split(':')
                            if len(parts) >= 2:  # En az ip:port
                                ip, port = parts[0], parts[1]
                                chrome_options.add_argument(f"--proxy-server=http://{ip}:{port}")
                    else:
                        # Standart proxy formatı
                        parts = proxy.split(':')
                        if len(parts) >= 2:  # En az ip:port
                            ip, port = parts[0], parts[1]
                            chrome_options.add_argument(f"--proxy-server=http://{ip}:{port}")
                            self.logger(f"Proxy: {ip}:{port}", "#8cffa0")
                except Exception as e:
                    self.logger(f"Proxy ayarlanırken hata: {e}", "#ff8c8c")
            
            # WebDriver'ı başlat
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            # Sayfayı yükle
            self.logger(f"Ziyaret ediliyor: {url}", "#8cffa0")
            driver.get(url)
            
            # Sayfa yüklenmesini bekle
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            self.logger(f"Sayfa yüklendi: {driver.title}", "#8cffa0")
            return driver
            
        except Exception as e:
            self.logger(f"Tarayıcı başlatılırken hata: {e}", "#ff8c8c")
            return None
    
    def simulate_scroll(self, driver, min_scrolls=5, max_scrolls=15):
        """Sayfa kaydırma davranışını simüle eder"""
        try:
            scroll_count = random.randint(min_scrolls, max_scrolls)
            self.logger(f"{scroll_count} kaydırma hareketi simüle ediliyor...", "#8cffa0")
            
            for i in range(scroll_count):
                # Rastgele bir mesafe kaydır (200-800px)
                scroll_amount = random.randint(200, 800)
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                
                # Kaydırma sonrası kısa bekleme (gerçekçi davranış için)
                time.sleep(random.uniform(1.0, 3.5))
                
                if i % 3 == 0:
                    self.logger("Sayfa kaydırıldı", "#8cffa0")
        except Exception as e:
            self.logger(f"Kaydırma sırasında hata: {e}", "#ff8c8c")
    
    def click_random_links(self, driver, min_clicks=2, max_clicks=5):
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
                self.logger("Tıklanabilir iç link bulunamadı.", "#ffcc8c")
                return
            
            # Rastgele sayıda link seç ve tıkla
            click_count = min(random.randint(min_clicks, max_clicks), len(internal_links))
            self.logger(f"{click_count} tıklama hareketi simüle ediliyor...", "#8cffa0")
            
            for i in range(click_count):
                # Rastgele bir link seç
                link = random.choice(internal_links)
                internal_links.remove(link)  # Aynı linke tekrar tıklamamak için
                
                link_text = link.text[:30] + "..." if link.text and len(link.text) > 30 else link.text
                self.logger(f"Tıklanıyor: {link_text if link_text else '[isimsiz link]'}", "#8cffa0")
                
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
                    self.logger(f"Link tıklama hatası: {e}", "#ffcc8c")
                    # Hata olursa ana sayfaya dön
                    try:
                        driver.get(driver.current_url)
                        time.sleep(2)
                    except:
                        pass
        
        except Exception as e:
            self.logger(f"Tıklama simülasyonu hatası: {e}", "#ff8c8c")
    
    def perform_visit(self, url, proxy=None):
        """Siteye tam bir ziyaret gerçekleştirir."""
        driver = None
        try:
            # Tarayıcıyı başlat
            driver = self.start_browser(url, proxy)
            if not driver:
                return False
            
            # Sitede geçirilecek süreyi belirle
            min_time = self.config.get("min_time_on_site", 30)
            max_time = self.config.get("max_time_on_site", 120)
            site_duration = random.randint(min_time, max_time)
            
            self.logger(f"Sitede {site_duration} saniye geçirilecek...", "#8cffa0")
            
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
                self.logger(f"Kalan süre: {remaining_time:.1f} saniye", "#8cffa0")
                
                # Sayfayı kaydır
                if remaining_time > 15:
                    self.simulate_scroll(driver)
                    time.sleep(random.uniform(1.0, 3.0))
                
                # Sayfa içi linklere tıkla
                if remaining_time > 30:
                    self.click_random_links(driver)
                    # İç sayfa gezintisi için biraz daha zaman ayır
                    time.sleep(random.uniform(2.0, 5.0))
                
                # Biraz daha bekle
                if remaining_time > 0:
                    wait_time = min(remaining_time, random.uniform(3.0, 8.0))
                    time.sleep(wait_time)
                    remaining_time -= wait_time
            
            total_duration = time.time() - start_time
            self.logger(f"✅ Ziyaret tamamlandı! Süre: {total_duration:.2f} saniye", "#8cffa0")
            return True
            
        except Exception as e:
            self.logger(f"❌ Ziyaret sırasında hata: {e}", "#ff8c8c")
            return False
            
        finally:
            # WebDriver'ı kapat
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def run_visits(self, url, count, proxy_list=None):
        """Belirtilen sayıda ziyaret gerçekleştirir."""
        if not url:
            self.logger("Hedef URL belirtilmedi!", "#ff8c8c")
            return
            
        self.running = True
        successful_visits = 0
        
        for i in range(count):
            if not self.running:
                break
                
            self.logger(f"Ziyaret #{i+1}/{count} başlatılıyor...", "#8cffa0")
            
            # Proxy seç
            proxy = self.get_proxy(proxy_list)
            proxy_text = proxy if proxy else "Doğrudan Bağlantı"
            self.logger(f"Kullanılan proxy: {proxy_text}", "#8cffa0")
            
            # Ziyareti gerçekleştir
            success = self.perform_visit(url, proxy)
            if success:
                successful_visits += 1
            
            # Sonraki ziyaret için bekle (ziyaretler arası 15-30 saniye)
            if i < count - 1 and self.running:
                wait_time = random.uniform(15, 30)
                self.logger(f"Sonraki ziyaret için {wait_time:.1f} saniye bekleniyor...", "#8cffa0")
                
                # Beklerken aralıklarla kontrol et (iptal edildi mi?)
                for _ in range(int(wait_time)):
                    if not self.running:
                        break
                    time.sleep(1)
        
        success_rate = (successful_visits / count) * 100 if count > 0 else 0
        self.logger(f"Selenium ziyaretleri tamamlandı: {successful_visits}/{count} başarılı ({success_rate:.1f}%)", "#8cffa0")
        self.running = False
    
    def start_visits(self, url, count, proxy_list=None):
        """Ziyaretleri arka planda başlat."""
        if self.running:
            self.logger("Zaten aktif bir selenium ziyaret işlemi var!", "#ffcc8c")
            return False
            
        if not url:
            self.logger("Hedef URL belirtilmedi!", "#ff8c8c")
            return False
            
        # Yeni thread oluştur
        self.thread = threading.Thread(target=self.run_visits, args=(url, count, proxy_list))
        self.thread.daemon = True
        self.thread.start()
        
        self.logger(f"Selenium ziyaretleri başlatıldı: {count} ziyaret", "#8cffa0")
        return True
    
    def stop_visits(self):
        """Aktif ziyaret işlemini durdur."""
        if not self.running:
            return False
            
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
            
        self.logger("Selenium ziyaretleri durduruldu", "#ffcc8c")
        return True 