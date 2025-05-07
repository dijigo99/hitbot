#!/usr/bin/env python3
import os
import random
import time
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ClickType(Enum):
    """Types of click behaviors."""
    DIRECT = "direct"         # Doğrudan ziyaret
    GOOGLE_REFERRAL = "google_referral"  # Google araması üzerinden
    EXTERNAL_LINK = "external_link"  # Farklı bir siteden gelme taklidi

class UserBehavior:
    """Simulates realistic user behavior on websites."""
    
    def __init__(self, logger_func=print):
        """Initialize user behavior simulator.
        
        Args:
            logger_func: Function to use for logging (default: print)
        """
        self.logger = logger_func
        
        # Load config from .env
        self.min_time_on_site = float(os.getenv('MIN_TIME_ON_SITE', 10))
        self.max_time_on_site = float(os.getenv('MAX_TIME_ON_SITE', 60))
        self.min_wait_before_request = float(os.getenv('MIN_WAIT_BEFORE_REQUEST', 2))
        self.max_wait_before_request = float(os.getenv('MAX_WAIT_BEFORE_REQUEST', 6))
        self.click_type_weights = {
            ClickType.DIRECT: int(os.getenv('WEIGHT_DIRECT_CLICK', 20)),
            ClickType.GOOGLE_REFERRAL: int(os.getenv('WEIGHT_GOOGLE_REFERRAL', 70)),
            ClickType.EXTERNAL_LINK: int(os.getenv('WEIGHT_EXTERNAL_LINK', 10))
        }
        self.external_referrers = [
            "https://www.facebook.com",
            "https://twitter.com",
            "https://www.linkedin.com",
            "https://www.instagram.com",
            "https://www.reddit.com"
        ]
        
        # Additional external referrers from env (comma-separated)
        if os.getenv('EXTERNAL_REFERRERS'):
            self.external_referrers.extend(os.getenv('EXTERNAL_REFERRERS').split(','))
    
    def wait_before_request(self):
        """Wait random time before making a request to simulate human delay.
        
        Returns:
            float: The time waited in seconds
        """
        wait_time = random.uniform(self.min_wait_before_request, self.max_wait_before_request)
        self.logger(f"İstek öncesi {wait_time:.2f} saniye bekleniyor...", "#8cffa0")
        time.sleep(wait_time)
        return wait_time
    
    def simulate_time_on_site(self):
        """Simulate time spent on site. 
        
        Returns:
            float: The simulated time spent on site in seconds
        """
        time_on_site = random.uniform(self.min_time_on_site, self.max_time_on_site)
        self.logger(f"Site üzerinde {time_on_site:.2f} saniye geçiriliyor...", "#8cffa0")
        
        # We'll do periodic activity to simulate realistic browsing behavior
        elapsed = 0
        while elapsed < time_on_site:
            sleep_duration = min(random.uniform(1, 5), time_on_site - elapsed)
            time.sleep(sleep_duration)
            elapsed += sleep_duration
            
            # Log some activities periodically
            if random.random() < 0.4:  # 40% chance for each pause
                scroll_distance = random.randint(100, 800)
                self.logger(f"Sayfa {scroll_distance}px kadar kaydırıldı", "#8cffa0")
            
            if random.random() < 0.2:  # 20% chance for each pause
                self.logger(f"Kullanıcı içeriği okuyor...", "#8cffa0")
        
        return time_on_site
    
    def get_random_click_type(self):
        """Get a random click type based on configured weights.
        
        Returns:
            ClickType: The selected click type
        """
        # Convert weights to a list of (type, weight) tuples
        weighted_types = [(click_type, weight) for click_type, weight in self.click_type_weights.items()]
        total_weight = sum(weight for _, weight in weighted_types)
        
        # Get a random number between 0 and total_weight
        r = random.uniform(0, total_weight)
        current = 0
        
        for click_type, weight in weighted_types:
            current += weight
            if r <= current:
                return click_type
        
        # Default to DIRECT in case of any issues
        return ClickType.DIRECT
    
    def get_referrer_for_click_type(self, click_type):
        """Get an appropriate referrer URL for the given click type.
        
        Args:
            click_type: ClickType enum value
            
        Returns:
            str: A referrer URL
        """
        if click_type == ClickType.GOOGLE_REFERRAL:
            return "https://www.google.com/search"
        elif click_type == ClickType.EXTERNAL_LINK:
            return random.choice(self.external_referrers)
        # For DIRECT, return None (no referrer)
        return None
    
    def simulate_scroll_pattern(self):
        """Simulate a realistic scroll pattern.
        
        Returns:
            list: List of scroll events (position, timing)
        """
        scroll_events = []
        # Simulate 2-8 scroll actions
        num_scrolls = random.randint(2, 8)
        
        current_position = 0
        for i in range(num_scrolls):
            # Wait 1-5 seconds between scrolls
            wait_time = random.uniform(1, 5)
            
            # Scroll down 100-600 pixels (occasionally scrolls back up)
            if i > 0 and random.random() < 0.2:  # 20% chance to scroll up
                scroll_amount = -random.randint(50, 300)
            else:
                scroll_amount = random.randint(100, 600)
            
            current_position += scroll_amount
            current_position = max(0, current_position)  # Can't scroll above 0
            
            scroll_events.append({
                "position": current_position,
                "time": wait_time,
                "direction": "up" if scroll_amount < 0 else "down"
            })
            
            self.logger(f"Scroll: {scroll_amount}px {'yukarı' if scroll_amount < 0 else 'aşağı'}, " 
                       f"Pozisyon: {current_position}px")
        
        return scroll_events
    
    def apply_behavior_to_session(self, session, click_type=None):
        """Apply behavior traits to a requests session.
        
        Args:
            session: requests.Session object to modify
            click_type: ClickType to use, or None for random
            
        Returns:
            tuple: (modified session, used click_type)
        """
        if click_type is None:
            click_type = self.get_random_click_type()
        
        # Log the click type
        self.logger(f"Tıklama tipi: {click_type.value}")
        
        # Set the appropriate referrer
        referrer = self.get_referrer_for_click_type(click_type)
        if referrer:
            session.headers.update({'Referer': referrer})
            self.logger(f"Referrer ayarlandı: {referrer}")
        
        return session, click_type


# Example usage
if __name__ == "__main__":
    # Set up environment variables for testing
    os.environ['MIN_TIME_ON_SITE'] = '5'
    os.environ['MAX_TIME_ON_SITE'] = '10'
    
    behavior = UserBehavior()
    
    # Test wait before request
    behavior.wait_before_request()
    
    # Test scroll pattern
    behavior.simulate_scroll_pattern()
    
    # Test time on site
    duration = behavior.simulate_time_on_site()
    print(f"Total time on site: {duration:.2f} seconds") 