#!/usr/bin/env python3
import os
import random
import time
from urllib.parse import quote, urlparse
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
    
    def perform_search(self, session, keyword=None):
        """Perform a Google search for the target domain with optional keyword.
        
        Args:
            session: requests.Session object with proper headers/cookies/proxy
            keyword: Optional keyword to include in search (default: None)
            
        Returns:
            (success, found_url): Tuple of success boolean and found URL
        """
        if not self.target_domain:
            self.logger("Hedef domain belirtilmemiş", "#ff8c8c")
            return False, None
        
        search_query = self.format_search_query(keyword, self.target_domain)
        google_search_url = f"https://{self.google_domain}/search?q={search_query}"
        self.logger(f"Google araması: {search_query.replace('+', ' ')}")

        try:
            # Perform the search
            response = session.get(
                google_search_url,
                timeout=self.timeout,
                headers={'Referer': f'https://{self.google_domain}/'},
                verify=False  # Not recommended for production
            )
            
            # Simulate human delay after search
            search_delay = self.get_delay(self.search_delay)
            self.logger(f"Arama sonrası {search_delay:.2f} saniye bekleniyor...")
            time.sleep(search_delay)

            if response.status_code != 200:
                self.logger(f"Google araması başarısız oldu, durum kodu: {response.status_code}", "#ff8c8c")
                return False, None

            # Parse search results
            soup = BeautifulSoup(response.text, 'html.parser')
            result_links = [a['href'] for a in soup.select('a[href^="http"]')]

            # Find the first link that contains our target domain
            target_link = next((link for link in result_links if self.target_domain in link), None)

            if target_link:
                self.logger(f"Arama sonucu bulundu: {target_link}", "#8cffa0")
                
                # Simulate user behavior if enabled
                if self.simulate_user_behavior:
                    self.logger("Kullanıcı davranışı simüle ediliyor...")
                    time.sleep(random.uniform(0.5, 1.5))  # Brief pause before clicking
                
                # Visit the site with Google referrer
                visit_response = session.get(
                    target_link,
                    timeout=self.timeout,
                    headers={'Referer': google_search_url},
                    verify=False  # Not recommended for production
                )
                self.logger(f"→ Arama sonucu ziyaret edildi: {visit_response.status_code}")
                return visit_response.status_code == 200, target_link
            else:
                self.logger("❌ Arama sonucunda domain bulunamadı", "#ff8c8c")
                return False, None

        except Exception as e:
            self.logger(f"Google araması sırasında hata: {e}", "#ff8c8c")
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