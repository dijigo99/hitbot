#!/usr/bin/env python3
import os
import time
import json
import random
import datetime
import threading
import schedule
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class HitScheduler:
    """Schedules and executes hit jobs at specified times."""
    
    def __init__(self, run_func, logger_func=print):
        """Initialize hit scheduler.
        
        Args:
            run_func: Function to call to execute a hit job
            logger_func: Function to use for logging (default: print)
        """
        self.logger = logger_func
        self.run_func = run_func
        self.running = False
        self.scheduler_thread = None
        
        # Load configuration from .env
        self.schedule_file = os.getenv('SCHEDULE_FILE', 'schedule.json')
        self.default_times = os.getenv('DEFAULT_SCHEDULE', '09:00,12:30,15:00,18:30').split(',')
        self.random_minutes = int(os.getenv('RANDOM_MINUTES_RANGE', 15))
        self.request_count_min = int(os.getenv('SCHEDULED_REQUESTS_MIN', 2))
        self.request_count_max = int(os.getenv('SCHEDULED_REQUESTS_MAX', 5))
        
        # Create schedule directory if needed
        self.schedule_dir = Path(self.schedule_file).parent
        if self.schedule_dir != Path('.'):
            os.makedirs(self.schedule_dir, exist_ok=True)
    
    def _get_randomized_time(self, time_str):
        """Add a random offset to a time string to randomize execution.
        
        Args:
            time_str: Time string in HH:MM format
            
        Returns:
            str: New time string with random offset applied
        """
        try:
            hours, minutes = map(int, time_str.strip().split(':'))
            
            # Add random offset (-random_minutes to +random_minutes)
            offset = random.randint(-self.random_minutes, self.random_minutes)
            
            # Create a datetime and add the offset
            dt = datetime.datetime.now().replace(
                hour=hours, minute=minutes, second=0, microsecond=0
            )
            dt += datetime.timedelta(minutes=offset)
            
            # Return as HH:MM format
            return dt.strftime('%H:%M')
        except Exception as e:
            self.logger(f"Saat randomizasyon hatası: {e} - Orijinal zaman kullanılıyor", "#ffcc8c")
            return time_str
    
    def _load_schedule(self):
        """Load schedule from file or use defaults.
        
        Returns:
            list: List of time strings in HH:MM format
        """
        try:
            if os.path.exists(self.schedule_file):
                with open(self.schedule_file, 'r') as f:
                    schedule_data = json.load(f)
                    
                    if isinstance(schedule_data, dict) and 'times' in schedule_data:
                        times = schedule_data['times']
                        self.logger(f"Zamanlama yüklendi: {len(times)} zaman noktası")
                        return times
            
            # Use default times if file doesn't exist or is invalid
            self.logger(f"Varsayılan zamanlama kullanılıyor: {', '.join(self.default_times)}", "#ffcc8c")
            return self.default_times
        
        except (json.JSONDecodeError, FileNotFoundError):
            self.logger(f"Zamanlama dosyası yüklenemedi, varsayılanlar kullanılıyor", "#ffcc8c")
            return self.default_times
    
    def _save_schedule(self, times):
        """Save schedule to file.
        
        Args:
            times: List of time strings in HH:MM format
            
        Returns:
            bool: Whether the save was successful
        """
        try:
            with open(self.schedule_file, 'w') as f:
                json.dump({'times': times}, f, indent=2)
            
            self.logger(f"Zamanlama kaydedildi: {len(times)} zaman noktası", "#8cffa0")
            return True
        except Exception as e:
            self.logger(f"Zamanlama kaydetme hatası: {e}", "#ff8c8c")
            return False
    
    def _run_job(self, time_str=None):
        """Run a scheduled job.
        
        Args:
            time_str: Time string when the job was scheduled to run (for logging)
        """
        # Randomize request count
        request_count = random.randint(self.request_count_min, self.request_count_max)
        
        # Log job execution
        now = datetime.datetime.now().strftime('%H:%M:%S')
        if time_str:
            self.logger(f"⏰ Zamanlanmış görev çalıştırılıyor ({time_str} zamanlaması) - {now} - {request_count} istek", "#8cffa0")
        else:
            self.logger(f"⏰ Manuel görev çalıştırılıyor - {now} - {request_count} istek", "#8cffa0")
        
        # Execute the run function
        try:
            # Get job settings - with small randomization for improved realism
            settings = {
                'request_count': request_count,
                'is_scheduled': True,
                'schedule_time': time_str
            }
            
            # Call the run function with settings
            self.run_func(settings)
            
        except Exception as e:
            self.logger(f"Zamanlanmış görev hatası: {e}", "#ff8c8c")
    
    def add_schedule_time(self, time_str):
        """Add a time to the schedule.
        
        Args:
            time_str: Time string in HH:MM format
            
        Returns:
            bool: Whether the time was added successfully
        """
        try:
            # Validate time format
            datetime.datetime.strptime(time_str, '%H:%M')
            
            # Load current schedule
            times = self._load_schedule()
            
            # Add new time if not already in the schedule
            if time_str not in times:
                times.append(time_str)
                times.sort()  # Sort times chronologically
                
                # Save updated schedule
                if self._save_schedule(times):
                    # If scheduler is running, update it
                    if self.running:
                        self.stop()
                        self.start()
                    
                    return True
            else:
                self.logger(f"Zaman zaten zamanlamada mevcut: {time_str}", "#ffcc8c")
            
            return False
        
        except ValueError:
            self.logger(f"Geçersiz zaman formatı: {time_str} - 'HH:MM' formatında olmalı", "#ff8c8c")
            return False
    
    def remove_schedule_time(self, time_str):
        """Remove a time from the schedule.
        
        Args:
            time_str: Time string in HH:MM format
            
        Returns:
            bool: Whether the time was removed successfully
        """
        # Load current schedule
        times = self._load_schedule()
        
        # Remove time if it exists
        if time_str in times:
            times.remove(time_str)
            
            # Save updated schedule
            if self._save_schedule(times):
                # If scheduler is running, update it
                if self.running:
                    self.stop()
                    self.start()
                
                return True
        else:
            self.logger(f"Zaman zamanlamada bulunamadı: {time_str}", "#ffcc8c")
        
        return False
    
    def get_schedule(self):
        """Get the current schedule.
        
        Returns:
            list: List of time strings in HH:MM format
        """
        return self._load_schedule()
    
    def get_next_run_time(self):
        """Get the next scheduled run time.
        
        Returns:
            str: Next scheduled run time in HH:MM format, or None if no schedules
        """
        if not self.running:
            return None
        
        # Get all scheduled jobs
        jobs = schedule.get_jobs()
        if not jobs:
            return None
        
        # Find the next job to run
        now = datetime.datetime.now()
        next_time = None
        min_diff = datetime.timedelta(days=1)
        
        for job in jobs:
            # Get the next run time for this job
            job_time = job.next_run
            
            # If the job runs today
            if job_time.date() == now.date():
                diff = job_time - now
                if diff.total_seconds() > 0 and diff < min_diff:
                    min_diff = diff
                    next_time = job_time.strftime('%H:%M')
        
        return next_time
    
    def _scheduler_loop(self):
        """Run the scheduler loop in a separate thread."""
        self.logger("⏰ Zamanlayıcı başlatıldı", "#8cffa0")
        
        while self.running:
            schedule.run_pending()
            time.sleep(1)
        
        self.logger("⏰ Zamanlayıcı durduruldu", "#ffcc8c")
    
    def start(self):
        """Start the scheduler."""
        if self.running:
            self.logger("Zamanlayıcı zaten çalışıyor", "#ffcc8c")
            return False
        
        # Clear previous schedule
        schedule.clear()
        
        # Load schedule
        times = self._load_schedule()
        
        if not times:
            self.logger("Zamanlama boş, zamanlayıcı başlatılmadı", "#ffcc8c")
            return False
        
        # Set up jobs with randomized times
        for time_str in times:
            # Add some randomness to the schedule to avoid patterns
            randomized_time = self._get_randomized_time(time_str)
            
            # Schedule the job
            schedule.every().day.at(randomized_time).do(self._run_job, time_str)
            self.logger(f"Görev zamanlandı: {time_str} ({randomized_time})")
        
        # Start the scheduler thread
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        return True
    
    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            self.logger("Zamanlayıcı zaten durdurulmuş", "#ffcc8c")
            return False
        
        # Stop the scheduler thread
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            self.scheduler_thread = None
        
        # Clear all jobs
        schedule.clear()
        
        return True
    
    def run_now(self):
        """Run a job immediately.
        
        Returns:
            bool: Whether the job was started successfully
        """
        # Run in a separate thread to avoid blocking
        thread = threading.Thread(target=self._run_job)
        thread.daemon = True
        thread.start()
        
        return True


# Example usage
if __name__ == "__main__":
    # Define a mock run function
    def mock_run(settings):
        print(f"Running mock job with settings: {settings}")
        time.sleep(2)  # Simulate some work
        print("Job completed")
    
    # Create a scheduler
    scheduler = HitScheduler(mock_run)
    
    # Get the current schedule
    print(f"Current schedule: {scheduler.get_schedule()}")
    
    # Add a new time
    scheduler.add_schedule_time("10:30")
    
    # Start the scheduler
    scheduler.start()
    
    # Get the next run time
    print(f"Next run time: {scheduler.get_next_run_time()}")
    
    # Run a job immediately
    scheduler.run_now()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Stop the scheduler on keyboard interrupt
        scheduler.stop()
        print("Scheduler stopped") 