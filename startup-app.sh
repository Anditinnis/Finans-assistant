#!/bin/bash

echo "=== Запуск всех сервисов ===" >> /home/uppcoder/app/startup_debug.log

# 1. Django сайт
pixi run -e web-django python manage.py runserver 0.0.0.0:8000 >> /home/uppcoder/app/django.log 2>&1 &

# 2. VK-бот с автоперезапуском
(
  while true; do
    pixi run -e web-django python bot.py >> /home/uppcoder/app/bot.log 2>&1
    echo "[watchdog] Бот упал, перезапуск через 10 секунд..." >> /home/uppcoder/app/bot.log
    sleep 10
  done
) &

wait