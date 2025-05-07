#!/usr/bin/env python3
import os
import csv
import json
import time
import socket
import datetime
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Analytics:
    """Analytics module for logging request data."""
    
    def __init__(self, logger_func=print):
        """Initialize analytics module.
        
        Args:
            logger_func: Function to use for logging (default: print)
        """
        self.logger = logger_func
        
        # Set up configuration from .env
        self.logs_directory = os.getenv('LOGS_DIRECTORY', 'logs')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.enable_csv_logging = os.getenv('ENABLE_CSV_LOGGING', 'true').lower() == 'true'
        self.enable_json_logging = os.getenv('ENABLE_JSON_LOGGING', 'false').lower() == 'true'
        
        # Create logs directory if it doesn't exist
        self._create_logs_directory()
        
        # Set up file logger
        self._setup_logger()
    
    def _create_logs_directory(self):
        """Create logs directory if it doesn't exist."""
        try:
            os.makedirs(self.logs_directory, exist_ok=True)
            self.logger(f"Logs klasörü: {self.logs_directory}")
        except Exception as e:
            self.logger(f"Logs klasörü oluşturulamadı: {e}", "#ff8c8c")
    
    def _setup_logger(self):
        """Set up file logger."""
        log_level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        level = log_level_map.get(self.log_level.upper(), logging.INFO)
        
        # Create a logger
        self.file_logger = logging.getLogger('hitbot')
        self.file_logger.setLevel(level)
        
        # Clear any existing handlers
        if self.file_logger.handlers:
            self.file_logger.handlers.clear()
        
        # Add file handler
        log_file = Path(self.logs_directory) / 'hitbot.log'
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.file_logger.addHandler(file_handler)
        
        self.file_logger.info("Logging başlatıldı")
    
    def _get_local_ip(self):
        """Get local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def _get_csv_filename(self):
        """Get CSV filename based on current date."""
        today = datetime.datetime.now().strftime("%Y%m%d")
        return Path(self.logs_directory) / f"{today}.csv"
    
    def _get_json_filename(self):
        """Get JSON filename based on current date."""
        today = datetime.datetime.now().strftime("%Y%m%d")
        return Path(self.logs_directory) / f"{today}.json"
    
    def _write_csv_header(self, filename):
        """Write CSV header if file doesn't exist."""
        if not os.path.exists(filename):
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'target_url', 'status_code', 'response_time', 'ip', 
                    'proxy', 'user_agent', 'profile', 'cookies_count', 'success'
                ])
    
    def log_request(self, data):
        """Log request data to file.
        
        Args:
            data: Dictionary containing request data with the following keys:
                - timestamp: Time of request (optional, will be added if not present)
                - target_url: URL that was requested
                - status_code: HTTP status code (int)
                - response_time: Response time in seconds (float)
                - proxy: Proxy used (or None)
                - user_agent: User agent string
                - profile: Browser profile used
                - cookies: Dictionary of cookies used
                - success: Whether the request was successful (bool)
                - error: Error message if any
        """
        # Ensure timestamp is present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.datetime.now().isoformat()
        
        # Get local IP
        data['ip'] = self._get_local_ip()
        
        # Calculate cookies count
        if 'cookies' in data:
            data['cookies_count'] = len(data.get('cookies', {}))
        
        # Log to file logger
        msg = f"Request: {data.get('target_url')} - Status: {data.get('status_code')} - " \
              f"Time: {data.get('response_time', 0):.2f}s - Success: {data.get('success', False)}"
        
        if data.get('success', False):
            self.file_logger.info(msg)
        else:
            error = data.get('error', 'Unknown error')
            self.file_logger.error(f"{msg} - Error: {error}")
        
        # Log to CSV file
        if self.enable_csv_logging:
            try:
                csv_file = self._get_csv_filename()
                self._write_csv_header(csv_file)
                
                with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        data.get('timestamp', ''),
                        data.get('target_url', ''),
                        data.get('status_code', ''),
                        data.get('response_time', ''),
                        data.get('ip', ''),
                        data.get('proxy', ''),
                        data.get('user_agent', ''),
                        data.get('profile', ''),
                        data.get('cookies_count', 0),
                        data.get('success', False)
                    ])
            except Exception as e:
                self.logger(f"CSV log yazma hatası: {e}", "#ff8c8c")
        
        # Log to JSON file
        if self.enable_json_logging:
            try:
                json_file = self._get_json_filename()
                
                # Read existing data
                existing_data = []
                if os.path.exists(json_file):
                    with open(json_file, 'r', encoding='utf-8') as f:
                        try:
                            existing_data = json.load(f)
                        except json.JSONDecodeError:
                            existing_data = []
                
                # Copy the data without the cookies (they can be too large)
                log_data = data.copy()
                if 'cookies' in log_data:
                    log_data['cookies'] = f"{log_data['cookies_count']} cookies"
                
                # Append new data
                existing_data.append(log_data)
                
                # Write back
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, indent=2, default=str)
            except Exception as e:
                self.logger(f"JSON log yazma hatası: {e}", "#ff8c8c")
        
        # Log summary to console
        success_emoji = "✅" if data.get('success', False) else "❌"
        self.logger(f"{success_emoji} {data.get('target_url')} - {data.get('status_code', 'N/A')} - " 
                    f"{data.get('response_time', 0):.2f}s - Proxy: {data.get('proxy', 'None')}",
                    "#8cffa0" if data.get('success', False) else "#ff8c8c")
    
    def log_summary(self, data):
        """Log summary data for a test run.
        
        Args:
            data: Dictionary containing summary data with the following keys:
                - timestamp: Time of summary (optional, will be added if not present)
                - test_duration: Total test duration in seconds
                - successful_requests: Number of successful requests
                - failed_requests: Number of failed requests
                - success_rate: Success rate as percentage
        """
        # Ensure timestamp is present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.datetime.now().isoformat()
        
        # Log to file logger
        msg = f"Test Summary - Duration: {data.get('test_duration', 0):.2f}s - " \
              f"Success: {data.get('successful_requests', 0)}/{data.get('successful_requests', 0) + data.get('failed_requests', 0)} " \
              f"({data.get('success_rate', 0):.2f}%)"
        
        self.file_logger.info(msg)
        
        # Log to summary file
        try:
            summary_file = Path(self.logs_directory) / 'summary.csv'
            header_needed = not os.path.exists(summary_file)
            
            with open(summary_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                if header_needed:
                    writer.writerow([
                        'timestamp', 'test_duration', 'successful_requests',
                        'failed_requests', 'total_requests', 'success_rate'
                    ])
                
                writer.writerow([
                    data.get('timestamp', ''),
                    data.get('test_duration', 0),
                    data.get('successful_requests', 0),
                    data.get('failed_requests', 0),
                    data.get('successful_requests', 0) + data.get('failed_requests', 0),
                    data.get('success_rate', 0)
                ])
        except Exception as e:
            self.logger(f"Özet log yazma hatası: {e}", "#ff8c8c")
        
        # Log to console
        self.logger(f"📊 Test Özeti - {data.get('successful_requests', 0)}/{data.get('successful_requests', 0) + data.get('failed_requests', 0)} " 
                    f"başarılı istek ({data.get('success_rate', 0):.2f}%) - {data.get('test_duration', 0):.2f}s sürdü",
                    "#8cffa0")

# Example usage
if __name__ == "__main__":
    # Create an analytics instance
    analytics = Analytics()
    
    # Create example request data
    request_data = {
        'target_url': 'https://example.com',
        'status_code': 200,
        'response_time': 0.5,
        'proxy': 'http://proxy.example.com:8080',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124',
        'profile': 'CHROME_DESKTOP',
        'cookies': {'session': 'abc123', 'user': 'test'},
        'success': True
    }
    
    # Log the request
    analytics.log_request(request_data)
    
    # Create and log a failed request
    failed_request = request_data.copy()
    failed_request['status_code'] = 404
    failed_request['success'] = False
    failed_request['error'] = 'Page not found'
    analytics.log_request(failed_request)
    
    # Log summary
    summary_data = {
        'test_duration': 10.5,
        'successful_requests': 1,
        'failed_requests': 1,
        'success_rate': 50.0
    }
    analytics.log_summary(summary_data) 