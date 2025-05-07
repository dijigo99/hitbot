#!/usr/bin/env python3
import os
import random
import time
from urllib.parse import quote, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GoogleSearch:
    """Google search simulator that finds target domain and visits it."""
    
    def __init__(self, logger_func=print):
        """Initialize Google search module.
        
        Args:
            logger_func: Function to use for logging (default: print)
        """
        self.logger = logger_func
        self.target_url = os.getenv('TARGET_URL', '')
        self.target_domain = self._extract_domain(self.target_url)
        self.search_delay = float(os.getenv('SEARCH_DELAY', 2))
        self.randomize_delays = os.getenv('RANDOMIZE_DELAYS', 'true').lower() == 'true'
        self.simulate_user_behavior = os.getenv('SIMULATE_USER_BEHAVIOR', 'true').lower() == 'true'
        self.google_domain = os.getenv('GOOGLE_DOMAIN', 'www.google.com')
        self.timeout = int(os.getenv('TIMEOUT', 10))
    
    def _extract_domain(self, url):
        """Extract domain from URL."""
        if not url:
            return None
        
        try:
            domain = urlparse(url).netloc
            if not domain:  # Fallback for URLs without protocol
                parts = url.split('/')
                domain = parts[0]
            return domain
        except Exception as e:
            self.logger(f"Domain çıkarma hatası: {e}", "#ff8c8c")
            return None
    
    def normalize_domain(self, url):
        """Normalize domain for comparison."""
        if not url:
            return ""
        
        try:
            domain = self._extract_domain(url)
            if not domain:
                return ""
            
            # Remove www. prefix if exists
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain.lower()
        except Exception as e:
            self.logger(f"Domain normalizasyon hatası: {e}", "#ff8c8c")
            return ""
    
    def extract_url_from_google_redirect(self, href):
        """Extract the actual URL from a Google redirect URL."""
        try:
            if href.startswith('/url?'):
                # Parse query parameters
                query = parse_qs(urlparse(href).query)
                if 'q' in query and query['q']:
                    return query['q'][0]  # Return the first 'q' parameter
            return href
        except Exception as e:
            self.logger(f"Google yönlendirme URL'si ayrıştırma hatası: {e}", "#ff8c8c")
            return href
    
    def get_delay(self, base_delay):
        """Get a randomized delay if randomize_delays is enabled."""
        if self.randomize_delays:
            # Randomize by ±30%
            variation = base_delay * 0.3
            return random.uniform(base_delay - variation, base_delay + variation)
        return base_delay
    
    def format_search_query(self, keyword, domain):
        """Format search query with keyword and domain."""
        if keyword:
            return quote(f"{keyword} {domain}")
        return quote(domain)
    
    def perform_search(self, session, keyword):
        """Perform a Google search with the given keyword and session.
        
        Args:
            session: A requests session object
            keyword: The keyword to search for
            
        Returns:
            tuple: (success, found_url)
        """
        if not keyword:
            self.logger("Anahtar kelime belirtilmedi!", "#ffcc8c")
            return False, None
            
        if not self.target_url:
            self.logger("Hedef URL belirtilmedi!", "#ff8c8c")
            return False, None
        
        try:
            # Format the query
            quoted_keyword = quote(keyword)
            search_url = f"https://www.google.com/search?q={quoted_keyword}"
            
            # Add some randomization to the Google search parameters
            search_params = [
                'hl=tr',                                          # Dil
                f'num={random.randint(10, 20)}',                  # Sonuç sayısı
                'safe=active' if random.random() < 0.7 else '',   # Güvenli arama
                'sourceid=chrome',                                # Chrome kaynak kimliği
                'ie=UTF-8',                                       # Karakter kodlaması
                'oq=' + quoted_keyword                            # Orijinal sorgu
            ]
            
            # Bazı parametreleri rastgele ekle
            if random.random() < 0.3:
                search_params.append(f"start={random.randint(0, 20)}")
            
            # Tüm parametreleri birleştir
            non_empty_params = [p for p in search_params if p]
            search_url = search_url + '&' + '&'.join(non_empty_params)
            
            self.logger(f"Google araması yapılıyor: '{keyword}'", "#8cffa0")
            
            # Render.com'da çalıştırılırken, Google'ın rate limit korumasını aşmak için 
            # ekstra bekleme süresi ekleyelim
            wait_time = random.uniform(3, 8)  # 3-8 saniye arası rastgele bir süre bekle
            self.logger(f"Google araması öncesi {wait_time:.2f} saniye bekleniyor...", "#ffcc8c")
            time.sleep(wait_time)
            
            try:
                timeout_val = self.timeout
                if self.randomize_delays:
                    # ±30% randomize timeout
                    timeout_val = timeout_val * random.uniform(0.7, 1.3)
                
                # Perform the search request with a proper User-Agent
                response = session.get(
                    search_url, 
                    timeout=timeout_val,
                    headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml',
                        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Cache-Control': 'max-age=0',
                        'Connection': 'keep-alive',
                        'DNT': '1',  # Do Not Track
                        'Upgrade-Insecure-Requests': '1'
                    }
                )
                
                # Check for proxy errors - catch HTTP errors
                if response.status_code >= 400:
                    # Rate limit hatası (429) için özel işleme
                    if response.status_code == 429:
                        self.logger(f"Google rate limit koruması (HTTP 429). 10-15 saniye bekleniyor...", "#ffcc8c")
                        time.sleep(random.uniform(10, 15))  # 10-15 saniye bekle
                        return False, None
                    
                    self.logger(f"Google arama hatası: HTTP {response.status_code}", "#ff8c8c")
                    return False, None
                
                # HTML'i ayrıştır
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Google'ın arama sonuçlarını bul (modern düzende)
                search_results = soup.select('div.g')
                
                if not search_results:
                    # Alternatif HTML düzeni dene
                    search_results = soup.select('div.tF2Cxc')
                
                # Google sayfasını ayrıştıramıyorsak, muhtemelen bot koruması ile karşılaştık
                if not search_results:
                    # Tüm heading etiketlerini kontrol et, belki captcha veya doğrulama mesajı vardır
                    headings = soup.find_all(['h1', 'h2', 'h3'])
                    for heading in headings:
                        text = heading.get_text().lower()
                        if 'robot' in text or 'automated' in text or 'unusual' in text or 'captcha' in text:
                            self.logger(f"Google bot koruması algılandı: {text}", "#ff8c8c")
                            # Yanıtın ilk 200 karakterini görüntüle, sorunu teşhis etmemize yardımcı olabilir
                            html_preview = response.text[:200] + "..."
                            self.logger(f"HTML önizleme: {html_preview}", "#ff8c8c")
                            return False, None
                    
                    self.logger("Google arama sonuçları bulunamadı.", "#ff8c8c")
                    return False, None
                
                # Her sonucu kontrol et
                domain_match = self.normalize_domain(self.target_url)
                for result in search_results:
                    link_elem = result.select_one('a[href]')
                    if not link_elem:
                        continue
                    
                    href = link_elem.get('href', '')
                    # Google'ın kendi yönlendirme URL'lerini atla
                    if href.startswith('/url?') or href.startswith('/search?'):
                        href = self.extract_url_from_google_redirect(href)
                    
                    # Hedef url'yi ara
                    if domain_match in self.normalize_domain(href):
                        # Link bulundu, bekle ve tıkla simüle et
                        self.logger(f"Hedef site Google sonuçlarında bulundu: {href}", "#8cffa0")
                        
                        # Arama sonuçları sayfasında geçirilen zamanı simüle et
                        search_delay = self.search_delay
                        if self.randomize_delays:
                            search_delay = search_delay * random.uniform(0.7, 1.3)
                        
                        self.logger(f"Arama sonuçları sayfasında {search_delay:.2f} saniye geçiriliyor...", "#8cffa0")
                        time.sleep(search_delay)
                        
                        # Şimdi sonuca tıklama simüle edelim - gerçek Google kullanıcıları gibi
                        # İlk olarak, sayfadaki linkin doğru URL'yi içerdiğini kontrol edelim
                        try:
                            # Tıklama simülasyonu için başlık ve metin içeriğini alıyoruz
                            title = result.select_one('h3')
                            title_text = title.get_text() if title else "Sonuç"
                            
                            self.logger(f"Tıklanan sonuç: \"{title_text}\"", "#8cffa0")
                            
                            # Tıklama isteğini gerçekleştir
                            click_response = session.get(
                                href, 
                                timeout=timeout_val,
                                headers={
                                    'Referer': search_url,
                                    'Accept': 'text/html,application/xhtml+xml,application/xml',
                                    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                                    'Connection': 'keep-alive',
                                    'Upgrade-Insecure-Requests': '1'
                                }
                            )
                            
                            # HTTP durum kodunu kontrol et
                            if click_response.status_code >= 400:
                                self.logger(f"Sonuca tıklama başarısız: HTTP {click_response.status_code}", "#ff8c8c")
                                return False, None
                            
                            self.logger(f"Başarıyla ziyaret edildi: {href}", "#8cffa0")
                            return True, href
                            
                        except Exception as e:
                            self.logger(f"Sonuca tıklama hatası: {e}", "#ff8c8c")
                            return False, None
                
                # Hedef site bulunamadı
                self.logger(f"Hedef site '{domain_match}' Google sonuçlarında bulunamadı", "#ffcc8c")
                return False, None
                
            except requests.exceptions.ProxyError as e:
                self.logger(f"Proxy hatası: {e}", "#ff8c8c")
                return False, None
            except requests.exceptions.Timeout as e:
                self.logger(f"Google araması zaman aşımı: {e}", "#ffcc8c")
                return False, None
            except requests.exceptions.SSLError as e:
                self.logger(f"SSL hatası: {e}", "#ff8c8c")
                return False, None
            except Exception as e:
                self.logger(f"Google arama hatası: {e}", "#ff8c8c")
                return False, None
                
        except Exception as e:
            self.logger(f"Genel Google arama hatası: {e}", "#ff8c8c")
            return False, None
    
    def direct_visit(self, session):
        """Directly visit the target URL without Google search.
        
        Args:
            session: requests.Session object with proper headers/cookies/proxy
            
        Returns:
            success: Boolean indicating if the visit was successful
        """
        if not self.target_url:
            self.logger("Hedef URL belirtilmemiş", "#ff8c8c")
            return False
        
        try:
            self.logger(f"Doğrudan ziyaret: {self.target_url}")
            response = session.get(
                self.target_url,
                timeout=self.timeout,
                headers={'Referer': f'https://{self.google_domain}/'},
                verify=False  # Not recommended for production
            )
            self.logger(f"→ Doğrudan ziyaret sonucu: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            self.logger(f"Doğrudan ziyaret sırasında hata: {e}", "#ff8c8c")
            return False


# Example usage
if __name__ == "__main__":
    # Set up environment variables for testing
    os.environ['TARGET_URL'] = 'https://example.com'
    os.environ['SEARCH_DELAY'] = '1'
    
    searcher = GoogleSearch()
    session = requests.Session()
    
    # Set up a default user agent
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    })
    
    # Perform a search
    success, url = searcher.perform_search(session, keyword="web site")
    print(f"Search result: {'Success' if success else 'Failed'}, URL: {url}") 