#!/usr/bin/env python3
import json
import random
import time
import os
import sys
import concurrent.futures
from urllib.parse import quote, urlparse
import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException, Timeout, ProxyError
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Get environment variables
TARGET_URL = os.getenv('TARGET_URL')
REQUEST_COUNT = int(os.getenv('REQUEST_COUNT', 25))
TIMEOUT = int(os.getenv('TIMEOUT', 10))
USE_DIRECT_CONNECTION = os.getenv('USE_DIRECT_CONNECTION', 'false').lower() == 'true'
MAX_PROXY_RETRIES = int(os.getenv('MAX_PROXY_RETRIES', 3))
# Default keywords if none provided in keywords.txt
DEFAULT_KEYWORDS = ["web sitesi", "blog", "hizmetler", "ürünler"]

def load_cookies():
    """Load cookies from cookies.json file"""
    try:
        with open('cookies.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading cookies: {e}")
        return {}

def load_proxies():
    """Load proxies from proxies.txt file"""
    try:
        with open('proxies.txt', 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError as e:
        print(f"Error loading proxies: {e}")
        return []

def load_user_agents():
    """Load user agents from user_agents.txt file"""
    try:
        with open('user_agents.txt', 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError as e:
        print(f"Error loading user agents: {e}")
        return ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"]

def load_keywords():
    """Load keywords from keywords.txt file"""
    try:
        with open('keywords.txt', 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
        if keywords:
            return keywords
        else:
            print("Warning: No keywords found in keywords.txt, using defaults")
            return DEFAULT_KEYWORDS
    except FileNotFoundError:
        print("Warning: keywords.txt not found, using default keywords")
        return DEFAULT_KEYWORDS

def test_proxy(proxy, timeout=5):
    """Test if a proxy is working"""
    try:
        proxies = {
            'http': proxy,
            'https': proxy
        }
        # Use a simple test URL
        response = requests.get('http://httpbin.org/ip', 
                                proxies=proxies, 
                                timeout=timeout,
                                verify=False)
        if response.status_code == 200:
            return True
        return False
    except Exception:
        return False

def get_working_proxies(proxy_list, max_workers=10):
    """Test proxies in parallel and return working ones"""
    working_proxies = []
    
    if not proxy_list:
        return working_proxies
    
    print(f"Testing {len(proxy_list)} proxies...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_proxy = {executor.submit(test_proxy, proxy): proxy for proxy in proxy_list}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_proxy)):
            proxy = future_to_proxy[future]
            try:
                if future.result():
                    working_proxies.append(proxy)
                    print(f"✓ Working proxy found: {proxy}")
            except Exception:
                pass
            
            # Print progress every 5 proxies
            if (i+1) % 5 == 0:
                print(f"Tested {i+1}/{len(proxy_list)} proxies. Found {len(working_proxies)} working.")
    
    print(f"Proxy testing completed. {len(working_proxies)}/{len(proxy_list)} proxies are working.")
    return working_proxies

def create_session(proxy, user_agent, cookies):
    """Create a session with the given proxy, user agent, and cookies"""
    session = requests.Session()
    
    # Configure proxy if not using direct connection
    if proxy and not USE_DIRECT_CONNECTION:
        try:
            if proxy.startswith('http://') or proxy.startswith('https://'):
                session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
            elif proxy.startswith('socks4://') or proxy.startswith('socks5://'):
                session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
        except Exception as e:
            print(f"Error setting up proxy: {e}")
    
    # Set user agent
    session.headers.update({
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    })
    
    # Add cookies
    for key, value in cookies.items():
        session.cookies.set(key, value, domain='.google.com')
    
    return session

def simulate_google_search(session, keyword, site_domain):
    """Simulate a Google search and click the result link if found"""
    # If a specific keyword is provided, use it along with the domain
    if keyword:
        search_query = quote(f"{keyword} {site_domain}")
    else:
        search_query = quote(site_domain)
        
    google_search_url = f"https://www.google.com/search?q={search_query}"
    print(f"Searching Google for: {search_query.replace('+', ' ')}")

    try:
        response = session.get(
            google_search_url,
            timeout=TIMEOUT,
            headers={'Referer': 'https://www.google.com/'},
            verify=not USE_DIRECT_CONNECTION
        )
        
        time.sleep(random.uniform(1, 3))  # İnsan davranışı benzetmesi

        if response.status_code != 200:
            print("Google search failed with status:", response.status_code)
            return False

        # HTML içinden linkleri çek
        soup = BeautifulSoup(response.text, 'html.parser')
        result_links = [a['href'] for a in soup.select('a[href^="http"]')]

        # Hedef domain'e ait ilk linki bul
        target_link = next((link for link in result_links if site_domain in link), None)

        if target_link:
            print(f"Found search result: {target_link}")
            # Google referer ile ziyaret et
            visit_response = session.get(
                target_link,
                timeout=TIMEOUT,
                headers={'Referer': google_search_url},
                verify=not USE_DIRECT_CONNECTION
            )
            print(f"→ Visited target via search result: {visit_response.status_code}")
            return visit_response.status_code == 200
        else:
            print("❌ No search result found for domain in Google search")
            return False

    except Exception as e:
        print(f"Error during Google search simulation: {e}")
        return USE_DIRECT_CONNECTION

def make_request_with_retry(proxy_list, user_agent, cookies, keywords):
    """Make a request with proxy retry mechanism"""
    # If direct connection or no proxies, try without proxy
    if USE_DIRECT_CONNECTION or not proxy_list:
        return make_request(None, user_agent, cookies, keywords)
    
    # Try with each proxy until success or max retries reached
    for _ in range(min(MAX_PROXY_RETRIES, len(proxy_list))):
        proxy = random.choice(proxy_list)
        print(f"Trying with proxy: {proxy}")
        if make_request(proxy, user_agent, cookies, keywords):
            return True
        # Remove the failed proxy from the list
        if proxy in proxy_list:
            proxy_list.remove(proxy)
    
    # If all proxies failed, try direct connection as fallback
    print("All proxy attempts failed. Falling back to direct connection.")
    return make_request(None, user_agent, cookies, keywords)

def make_request(proxy, user_agent, cookies, keywords):
    """Make a request to the target URL using the given proxy, user agent, and cookies"""
    if not TARGET_URL:
        print("Error: TARGET_URL not set in .env file")
        return False
    
    # Extract domain from TARGET_URL for the search query
    try:
        domain = urlparse(TARGET_URL).netloc
    except:
        domain = TARGET_URL.replace('https://', '').replace('http://', '').split('/')[0]
    
    session = create_session(proxy, user_agent, cookies)
    
    # Choose a random keyword from the list
    keyword = random.choice(keywords) if keywords else None
    
    # First simulate a Google search
    search_success = simulate_google_search(session, keyword, domain)
    
    if not search_success and not USE_DIRECT_CONNECTION:
        print(f"Failed to simulate Google search using proxy: {proxy}")
        return False
    
    # Then visit the target URL with Google as referer
    try:
        response = session.get(
            TARGET_URL,
            timeout=TIMEOUT,
            headers={'Referer': 'https://www.google.com/search'},
            verify=False if USE_DIRECT_CONNECTION else True  # Allow skipping SSL verification in test mode
        )
        
        print(f"Request to {TARGET_URL} via {'direct connection' if USE_DIRECT_CONNECTION or not proxy else proxy}")
        print(f"Status: {response.status_code}")
        print(f"Response size: {len(response.content)} bytes")
        return True
    except Timeout:
        print(f"Timeout error with {'direct connection' if USE_DIRECT_CONNECTION or not proxy else proxy}")
    except ProxyError:
        print(f"Proxy error: {proxy}")
    except RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    return False

def main():
    """Main function"""
    global USE_DIRECT_CONNECTION
    
    # Check for required files
    if not os.path.exists('.env'):
        print("Warning: .env file not found. Using default settings.")
    
    # Load necessary data
    cookies = load_cookies()
    proxies = load_proxies()
    user_agents = load_user_agents()
    keywords = load_keywords()
    
    # Filter out non-working proxies if not using direct connection
    working_proxies = []
    if not USE_DIRECT_CONNECTION and proxies:
        working_proxies = get_working_proxies(proxies)
        if not working_proxies:
            print("Warning: No working proxies found. Consider setting USE_DIRECT_CONNECTION=true in .env")
            if input("Continue with direct connection? (y/n): ").lower() == 'y':
                USE_DIRECT_CONNECTION = True
            else:
                print("Exiting.")
                sys.exit(1)
    
    # Validate data
    if not cookies:
        print("Warning: No cookies loaded")
    
    if not user_agents:
        print("Warning: No user agents loaded. Using default.")
    
    # Print configuration
    print(f"Target URL: {TARGET_URL}")
    print(f"Request count: {REQUEST_COUNT}")
    print(f"Timeout: {TIMEOUT} seconds")
    print(f"Connection mode: {'Direct (no proxy)' if USE_DIRECT_CONNECTION else 'Proxy'}")
    if not USE_DIRECT_CONNECTION:
        print(f"Loaded {len(working_proxies)}/{len(proxies)} working proxies")
    print(f"Loaded {len(user_agents)} user agents")
    print(f"Loaded {len(cookies)} cookies")
    print(f"Loaded {len(keywords)} keywords")
    print("=" * 40)
    
    # Make requests
    successful_requests = 0
    total_attempts = 0
    
    for i in range(REQUEST_COUNT):
        user_agent = random.choice(user_agents) if user_agents else None
        
        print(f"\nRequest {i+1}/{REQUEST_COUNT}")
        total_attempts += 1
        
        if USE_DIRECT_CONNECTION:
            success = make_request(None, user_agent, cookies, keywords)
        else:
            success = make_request_with_retry(working_proxies, user_agent, cookies, keywords)
        
        if success:
            successful_requests += 1
        
        # Random delay between requests to appear more human-like
        if i < REQUEST_COUNT - 1:
            delay = random.uniform(2, 5)
            print(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
    
    # Print summary
    print("\n" + "=" * 40)
    print(f"Summary: {successful_requests}/{REQUEST_COUNT} successful requests")
    print(f"Success rate: {(successful_requests/REQUEST_COUNT)*100:.2f}%")

if __name__ == "__main__":
    try:
        # Disable insecure request warnings in direct connection mode
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        main()
    except KeyboardInterrupt:
        print("\nScript terminated by user.")
        sys.exit(0) 