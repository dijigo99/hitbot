#!/usr/bin/env python3
import os
import random
import json
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DeviceType(Enum):
    """Types of devices for user agents."""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"

class BrowserType(Enum):
    """Types of browsers for user agents."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"
    OPERA = "opera"

class UserProfile:
    """Manages user profiles and user agents."""
    
    def __init__(self, logger_func=print):
        """Initialize user profile manager.
        
        Args:
            logger_func: Function to use for logging (default: print)
        """
        self.logger = logger_func
        
        # Load configuration from .env
        self.use_random_profile = os.getenv('USE_RANDOM_PROFILE', 'true').lower() == 'true'
        self.default_profile = os.getenv('DEFAULT_PROFILE', 'CHROME_DESKTOP')
        self.user_agents_file = os.getenv('USER_AGENTS_FILE', 'user_agents.txt')
        
        # Load user agents from file
        self.user_agents = self._load_user_agents()
        
        # Define browser profiles
        self.profiles = {
            # Desktop profiles
            'CHROME_DESKTOP': {
                'browser': BrowserType.CHROME,
                'device': DeviceType.DESKTOP,
                'headers': {
                    'User-Agent': self._get_random_user_agent(BrowserType.CHROME, DeviceType.DESKTOP),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-User': '?1',
                    'Sec-Fetch-Dest': 'document',
                }
            },
            'FIREFOX_DESKTOP': {
                'browser': BrowserType.FIREFOX,
                'device': DeviceType.DESKTOP,
                'headers': {
                    'User-Agent': self._get_random_user_agent(BrowserType.FIREFOX, DeviceType.DESKTOP),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-User': '?1',
                    'Sec-Fetch-Dest': 'document',
                    'DNT': '1',  # Firefox often has DNT set
                }
            },
            'EDGE_DESKTOP': {
                'browser': BrowserType.EDGE,
                'device': DeviceType.DESKTOP,
                'headers': {
                    'User-Agent': self._get_random_user_agent(BrowserType.EDGE, DeviceType.DESKTOP),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-User': '?1',
                    'Sec-Fetch-Dest': 'document',
                }
            },
            
            # Mobile profiles
            'CHROME_MOBILE': {
                'browser': BrowserType.CHROME,
                'device': DeviceType.MOBILE,
                'headers': {
                    'User-Agent': self._get_random_user_agent(BrowserType.CHROME, DeviceType.MOBILE),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-User': '?1',
                    'Sec-Fetch-Dest': 'document',
                    'Viewport-Width': '412',
                    'Screen-Width': '412',
                }
            },
            'SAFARI_MOBILE': {
                'browser': BrowserType.SAFARI,
                'device': DeviceType.MOBILE,
                'headers': {
                    'User-Agent': self._get_random_user_agent(BrowserType.SAFARI, DeviceType.MOBILE),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0',
                    'Viewport-Width': '375',
                    'Screen-Width': '375',
                }
            }
        }
        
        # Allow custom profiles from .env
        self._load_custom_profiles()
    
    def _load_user_agents(self):
        """Load user agents from file and categorize them.
        
        Returns:
            dict: Dictionary of user agents by browser and device type
        """
        user_agents = {
            # Initialize with empty lists for all browser/device combinations
            browser.value: {device.value: [] for device in DeviceType}
            for browser in BrowserType
        }
        
        # Default user agents in case file is missing
        default_agents = {
            BrowserType.CHROME.value: {
                DeviceType.DESKTOP.value: [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                ],
                DeviceType.MOBILE.value: [
                    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
                ]
            },
            BrowserType.FIREFOX.value: {
                DeviceType.DESKTOP.value: [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
                ],
                DeviceType.MOBILE.value: [
                    "Mozilla/5.0 (Android 12; Mobile; rv:98.0) Gecko/98.0 Firefox/98.0"
                ]
            }
        }
        
        try:
            with open(self.user_agents_file, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
                
                for line in lines:
                    # Categorize each user agent based on its content
                    if "Chrome" in line and "Mobile" in line:
                        user_agents[BrowserType.CHROME.value][DeviceType.MOBILE.value].append(line)
                    elif "Chrome" in line:
                        user_agents[BrowserType.CHROME.value][DeviceType.DESKTOP.value].append(line)
                    elif "Firefox" in line and "Mobile" in line:
                        user_agents[BrowserType.FIREFOX.value][DeviceType.MOBILE.value].append(line)
                    elif "Firefox" in line:
                        user_agents[BrowserType.FIREFOX.value][DeviceType.DESKTOP.value].append(line)
                    elif "Safari" in line and "Mobile" in line:
                        user_agents[BrowserType.SAFARI.value][DeviceType.MOBILE.value].append(line)
                    elif "Safari" in line:
                        user_agents[BrowserType.SAFARI.value][DeviceType.DESKTOP.value].append(line)
                    elif "Edge" in line:
                        user_agents[BrowserType.EDGE.value][DeviceType.DESKTOP.value].append(line)
                    elif "Opera" in line:
                        user_agents[BrowserType.OPERA.value][DeviceType.DESKTOP.value].append(line)
                
                # Count loaded user agents
                total_agents = sum(len(agents) for browser_agents in user_agents.values() 
                                  for agents in browser_agents.values())
                self.logger(f"{total_agents} adet user agent yüklendi.")
                
                # For any empty categories, use defaults if available
                for browser in BrowserType:
                    for device in DeviceType:
                        if not user_agents[browser.value][device.value]:
                            if (browser.value in default_agents and 
                                device.value in default_agents[browser.value]):
                                user_agents[browser.value][device.value] = default_agents[browser.value][device.value]
        
        except FileNotFoundError:
            self.logger(f"Uyarı: {self.user_agents_file} dosyası bulunamadı. Varsayılan user agent'lar kullanılacak.", "#ffcc8c")
            
            # Use default agents if file not found
            for browser in BrowserType:
                for device in DeviceType:
                    if (browser.value in default_agents and 
                        device.value in default_agents[browser.value]):
                        user_agents[browser.value][device.value] = default_agents[browser.value][device.value]
        
        return user_agents
    
    def _load_custom_profiles(self):
        """Load custom profiles from .env if defined."""
        custom_profiles_str = os.getenv('CUSTOM_PROFILES', '')
        
        if custom_profiles_str:
            try:
                custom_profiles = json.loads(custom_profiles_str)
                for profile_name, profile_data in custom_profiles.items():
                    if 'browser' in profile_data and 'device' in profile_data and 'headers' in profile_data:
                        self.profiles[profile_name] = profile_data
                        self.logger(f"Özel profil yüklendi: {profile_name}")
            except (json.JSONDecodeError, ValueError) as e:
                self.logger(f"Özel profil yükleme hatası: {e}", "#ff8c8c")
    
    def _get_random_user_agent(self, browser, device):
        """Get a random user agent for the specified browser and device type.
        
        Args:
            browser: BrowserType enum value
            device: DeviceType enum value
            
        Returns:
            str: A user agent string
        """
        agents = self.user_agents[browser.value][device.value]
        
        if not agents:
            # If no agents available for this combination, get from any browser of the same device type
            for browser_value in self.user_agents:
                if agents := self.user_agents[browser_value][device.value]:
                    break
        
        if not agents:
            # If still no agents, use a generic one
            if device == DeviceType.MOBILE:
                return "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
            else:
                return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        
        return random.choice(agents)
    
    def get_profile(self, profile_name=None):
        """Get a user profile by name or a random one.
        
        Args:
            profile_name: Name of the profile to get, or None for default/random
            
        Returns:
            dict: The selected profile data
        """
        if profile_name is None:
            # Use the configured default or random behavior
            if self.use_random_profile:
                profile_name = random.choice(list(self.profiles.keys()))
            else:
                profile_name = self.default_profile
        
        # Ensure the profile exists
        if profile_name not in self.profiles:
            self.logger(f"Profil bulunamadı: {profile_name}, varsayılan profil kullanılıyor.", "#ffcc8c")
            profile_name = self.default_profile
            
            # If default profile also doesn't exist, use the first available
            if profile_name not in self.profiles:
                profile_name = next(iter(self.profiles.keys()))
        
        # Log the selected profile
        self.logger(f"Kullanılan profil: {profile_name}")
        
        return self.profiles[profile_name]
    
    def apply_profile_to_session(self, session, profile_name=None):
        """Apply a user profile to a requests session.
        
        Args:
            session: requests.Session object to modify
            profile_name: Name of the profile to apply, or None for default/random
            
        Returns:
            requests.Session: The modified session
        """
        profile = self.get_profile(profile_name)
        
        # Apply headers from the profile
        session.headers.update(profile['headers'])
        
        # Log the user agent being used
        self.logger(f"Kullanılan user agent: {profile['headers'].get('User-Agent', 'Belirtilmemiş')}")
        
        return session


# Example usage
if __name__ == "__main__":
    profile_manager = UserProfile()
    
    # Get a random profile
    profile = profile_manager.get_profile()
    print(f"Random profile: {profile['browser'].value} on {profile['device'].value}")
    print(f"User-Agent: {profile['headers']['User-Agent']}")
    
    # Get a specific profile
    chrome_desktop = profile_manager.get_profile("CHROME_DESKTOP")
    print(f"\nSpecific profile: {chrome_desktop['browser'].value} on {chrome_desktop['device'].value}")
    print(f"User-Agent: {chrome_desktop['headers']['User-Agent']}") 