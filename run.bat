@echo off
set PORT=5000
echo Port 5000 üzerinde çalışmaya başlıyor...
python -c "import os; os.environ['PORT'] = '5000'; __import__('app')" 