#!/bin/bash

echo "=== Запуск всех сервисов ==="

# 1. Django сайт на порту 8000 (Uppcoder ожидает его здесь)
pixi run -e web-django python manage.py runserver 0.0.0.0:8000 &

# 2. FastAPI (API для бота) на порту 8001
pixi run -e web-django uvicorn main:app --host 0.0.0.0 --port 8001 &

# 3. VK-бот
pixi run -e web-django python bot.py &

# Ждём, чтобы контейнер не завершился
wait