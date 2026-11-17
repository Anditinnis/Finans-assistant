#!/bin/bash

# Django сайт уже работает, его не трогаем.
# Запускаем API (FastAPI) на порту 8001
pixi run -e web-django uvicorn main:app --host 0.0.0.0 --port 8001 &

# Запускаем VK-бота
pixi run -e web-django python bot.py &

# Ждём, чтобы контейнер не закрылся
wait