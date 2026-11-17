cat << 'EOF' > /home/uppcoder/app/startup-app.sh
#!/bin/bash

echo "=== Запуск всех сервисов ===" >> /home/uppcoder/app/startup_debug.log

# 1. Django сайт
pixi run -e web-django python manage.py runserver 0.0.0.0:8000 >> /home/uppcoder/app/django.log 2>&1 &

# 2. FastAPI
pixi run -e web-django uvicorn main:app --host 0.0.0.0 --port 8001 >> /home/uppcoder/app/api.log 2>&1 &

# 3. VK-бот
pixi run -e web-django python bot.py >> /home/uppcoder/app/bot.log 2>&1 &

wait
EOF