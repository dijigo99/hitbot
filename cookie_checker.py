#!/usr/bin/env python3
import os
import json
import time
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CookieChecker:
    """Checks cookie files for required values and validity."""
    
    # Critical Google cookies that should be present
    CRITICAL_GOOGLE_COOKIES = [
        'NID',       # Google search cookie
        'SID',       # Session ID
        'HSID',      # Security cookie
        'SSID',      # Secure cookie
        'APISID',    # API cookie
        'SAPISID',   # Secure API cookie
        '1P_JAR',    # Google personalization
        'SIDCC',     # Security cookie
        '__Secure-1PSID',  # Secure session ID
        '__Secure-3PSIDCC',  # Session control
    ]
    
    # Cookies with shorter expiration (check more frequently)
    SHORT_EXPIRY_COOKIES = [
        '1P_JAR',
        'SIDCC',
        '__Secure-3PSIDCC',
    ]
    
    def __init__(self, logger_func=print):
        """Initialize cookie checker.
        
        Args:
            logger_func: Function to use for logging (default: print)
        """
        self.logger = logger_func
        
        # Load configuration from .env
        self.cookies_file = os.getenv('COOKIES_FILE', 'cookies.json')
        self.backup_dir = os.getenv('COOKIE_BACKUP_DIR', 'cookie_backups')
        self.min_cookies = int(os.getenv('MIN_REQUIRED_COOKIES', 5))
        self.cookie_expiry_warning_days = int(os.getenv('COOKIE_EXPIRY_WARNING_DAYS', 7))
        
        # Create backup directory if it doesn't exist
        self._create_backup_dir()
    
    def _create_backup_dir(self):
        """Create cookie backup directory if it doesn't exist."""
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            self.logger(f"Cookie yedek klasörü: {self.backup_dir}")
        except Exception as e:
            self.logger(f"Cookie yedek klasörü oluşturulamadı: {e}", "#ff8c8c")
    
    def _backup_cookies(self, cookies):
        """Backup current cookies with timestamp."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = Path(self.backup_dir) / f"cookies_{timestamp}.json"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            
            self.logger(f"Cookie'ler yedeklendi: {backup_file}")
            return True
        except Exception as e:
            self.logger(f"Cookie yedekleme hatası: {e}", "#ff8c8c")
            return False
    
    def load_cookies(self):
        """Load cookies from file.
        
        Returns:
            dict: The loaded cookies or empty dict if file doesn't exist
        """
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                self.logger(f"Yüklenen cookie sayısı: {len(cookies)}")
                return cookies
        except FileNotFoundError:
            self.logger(f"Cookie dosyası bulunamadı: {self.cookies_file}", "#ff8c8c")
            return {}
        except json.JSONDecodeError:
            self.logger(f"Cookie dosyası geçerli JSON formatında değil: {self.cookies_file}", "#ff8c8c")
            return {}
        except Exception as e:
            self.logger(f"Cookie dosyası yükleme hatası: {e}", "#ff8c8c")
            return {}
    
    def save_cookies(self, cookies):
        """Save cookies to file.
        
        Args:
            cookies: Dict of cookies to save
            
        Returns:
            bool: Whether the save was successful
        """
        try:
            # First backup existing cookies if any
            if os.path.exists(self.cookies_file):
                existing_cookies = self.load_cookies()
                if existing_cookies:
                    self._backup_cookies(existing_cookies)
            
            # Save new cookies
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            
            self.logger(f"Cookie'ler kaydedildi: {len(cookies)} adet", "#8cffa0")
            return True
        except Exception as e:
            self.logger(f"Cookie kaydetme hatası: {e}", "#ff8c8c")
            return False
    
    def check_cookies(self):
        """Check if cookies exist and contain critical values.
        
        Returns:
            tuple: (is_ok, missing_cookies, status) where:
                - is_ok: Boolean indicating if cookies are ok
                - missing_cookies: List of missing critical cookies
                - status: Status description string
        """
        cookies = self.load_cookies()
        
        if not cookies:
            return False, self.CRITICAL_GOOGLE_COOKIES, "Cookie dosyası bulunamadı veya boş"
        
        # Check if we have minimum number of cookies
        if len(cookies) < self.min_cookies:
            return False, [], f"Yetersiz cookie sayısı: {len(cookies)}/{self.min_cookies}"
        
        # Check for critical cookies
        missing_cookies = [cookie for cookie in self.CRITICAL_GOOGLE_COOKIES if cookie not in cookies]
        
        if missing_cookies:
            self.logger(f"Eksik kritik cookie'ler: {', '.join(missing_cookies)}", "#ffcc8c")
            return False, missing_cookies, f"Eksik kritik cookie'ler: {len(missing_cookies)} adet"
        
        # Check expiry of cookies if they have expiry dates
        near_expiry = []
        today = time.time()
        warning_seconds = self.cookie_expiry_warning_days * 24 * 60 * 60
        
        for cookie_name in self.SHORT_EXPIRY_COOKIES:
            if cookie_name in cookies and 'expires' in cookies[cookie_name]:
                try:
                    expires = cookies[cookie_name]['expires']
                    if isinstance(expires, (int, float)) and expires - today < warning_seconds:
                        near_expiry.append(cookie_name)
                except (ValueError, TypeError):
                    pass  # Skip if we can't parse expiry
        
        if near_expiry:
            self.logger(f"Süresi yakında dolacak cookie'ler: {', '.join(near_expiry)}", "#ffcc8c")
            return True, [], f"Süresi yakında dolacak cookie'ler: {len(near_expiry)} adet"
        
        return True, [], f"Cookie'ler geçerli: {len(cookies)} adet"
    
    def import_cookies_from_json(self, json_str):
        """Import cookies from a JSON string.
        
        Args:
            json_str: JSON string containing cookies
            
        Returns:
            tuple: (success, message) where:
                - success: Boolean indicating if import was successful
                - message: Status message
        """
        try:
            cookies = json.loads(json_str)
            
            if not isinstance(cookies, dict):
                return False, "Geçersiz JSON formatı: dictionary olmalı"
            
            if not cookies:
                return False, "Boş cookie verileri"
            
            # Save the cookies
            if self.save_cookies(cookies):
                # Re-check the cookies
                is_ok, missing, status = self.check_cookies()
                if is_ok:
                    return True, f"Cookie'ler başarıyla içe aktarıldı: {len(cookies)} adet"
                else:
                    return False, f"Cookie'ler kaydedildi ancak eksikler var: {status}"
            else:
                return False, "Cookie'ler kaydedilemedi"
        
        except json.JSONDecodeError:
            return False, "Geçersiz JSON formatı"
        except Exception as e:
            return False, f"Cookie içe aktarma hatası: {e}"
    
    def get_cookie_summary(self):
        """Get a summary of the cookies.
        
        Returns:
            dict: Summary information about cookies
        """
        cookies = self.load_cookies()
        
        if not cookies:
            return {
                'count': 0,
                'has_critical': False,
                'missing_critical': self.CRITICAL_GOOGLE_COOKIES,
                'status': "Cookies not found",
                'valid': False
            }
        
        # Check for critical cookies
        missing_critical = [cookie for cookie in self.CRITICAL_GOOGLE_COOKIES if cookie not in cookies]
        has_all_critical = not missing_critical
        
        # Get list of found critical cookies
        found_critical = [cookie for cookie in self.CRITICAL_GOOGLE_COOKIES if cookie in cookies]
        
        # Check cookie expiry
        near_expiry = []
        today = time.time()
        warning_seconds = self.cookie_expiry_warning_days * 24 * 60 * 60
        
        for cookie_name, cookie_data in cookies.items():
            if isinstance(cookie_data, dict) and 'expires' in cookie_data:
                try:
                    expires = cookie_data['expires']
                    if isinstance(expires, (int, float)) and expires - today < warning_seconds:
                        near_expiry.append(cookie_name)
                except (ValueError, TypeError):
                    pass
        
        # Determine status
        if not has_all_critical:
            status = f"Missing {len(missing_critical)} critical cookies"
            valid = False
        elif near_expiry:
            status = f"{len(near_expiry)} cookies expiring soon"
            valid = True
        else:
            status = "All cookies valid"
            valid = True
        
        return {
            'count': len(cookies),
            'has_critical': has_all_critical,
            'critical_found': found_critical,
            'missing_critical': missing_critical,
            'near_expiry': near_expiry,
            'status': status,
            'valid': valid
        }


# Example usage
if __name__ == "__main__":
    checker = CookieChecker()
    
    # Check cookies
    is_ok, missing, status = checker.check_cookies()
    print(f"Cookie status: {status}")
    print(f"Valid: {is_ok}")
    
    if missing:
        print(f"Missing cookies: {', '.join(missing)}")
    
    # Get summary
    summary = checker.get_cookie_summary()
    print(f"\nCookie summary: {summary['status']}")
    print(f"Cookie count: {summary['count']}")
    print(f"Has all critical cookies: {summary['has_critical']}")
    
    if not summary['has_critical']:
        print(f"Missing critical cookies: {', '.join(summary['missing_critical'])}") 