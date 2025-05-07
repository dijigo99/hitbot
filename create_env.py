#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UTF-8 formatında .env dosyası oluşturan yardımcı script
"""

import os

env_content = """TARGET_URL=https://hepsiburada.com
REQUEST_COUNT=10
TIMEOUT=10
USE_DIRECT_CONNECTION=true
MAX_PROXY_RETRIES=3
SEARCH_DELAY=2
REQUEST_DELAY=3
RANDOMIZE_DELAYS=true
SIMULATE_USER_BEHAVIOR=true

# Zamanlayıcı Ayarları
SCHEDULE_FILE=schedule.json
DEFAULT_SCHEDULE=09:00,12:30,15:00,18:30
RANDOM_MINUTES_RANGE=15
SCHEDULED_REQUESTS_MIN=2
SCHEDULED_REQUESTS_MAX=5
START_SCHEDULER_ON_BOOT=false

# Davranış Ayarları
MIN_TIME_ON_SITE=20
MAX_TIME_ON_SITE=60
WEIGHT_DIRECT_CLICK=20
WEIGHT_GOOGLE_REFERRAL=60
WEIGHT_EXTERNAL_LINK=20
EXTERNAL_REFERRERS=facebook.com,twitter.com,instagram.com

# Profil Ayarları
USE_RANDOM_PROFILE=true
DEFAULT_PROFILE=CHROME_DESKTOP
"""

# .env dosyasını UTF-8 formatında oluştur
with open('.env', 'w', encoding='utf-8') as f:
    f.write(env_content)

print(".env dosyası UTF-8 formatında başarıyla oluşturuldu!") 