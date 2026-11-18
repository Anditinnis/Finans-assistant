import os
import vk_api
import requests
import time

from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "super-secret-key-change-me")
SITE_URL = os.getenv("SITE_URL", "https://portal.uppcoder.com/cust-portal/stacks/2572")

GROUP_ID = 243085760

if not VK_TOKEN:
    raise RuntimeError("VK_TOKEN не найден в .env")

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

print("VK-бот запущен!")

user_states = {}


# ============================================================
# УТИЛИТЫ
# ============================================================
def touch_heartbeat():
    try:
        with open('bot_heartbeat.txt', 'w') as f:
            f.write(str(time.time()))
    except Exception:
        pass


def api_post(path, data):
    try:
        return requests.post(
            f"{API_URL}{path}",
            json=data,
            headers={"x-api-key": API_SECRET_KEY},
            timeout=10
        )
    except requests.RequestException as e:
        print(f"API error: {e}")
        return None


def api_get(path, params=None):
    try:
        return requests.get(
            f"{API_URL}{path}",
            params=params,
            headers={"x-api-key": API_SECRET_KEY},
            timeout=10
        )
    except requests.RequestException as e:
        print(f"API error: {e}")
        return None


def is_vk_linked(vk_id):
    resp = api_get(f"/api/users/by-vk/{vk_id}/")
    return resp is not None and resp.status_code == 200


def get_vk_avatar_url(vk_id):
    """Получает ссылку на аватар пользователя ВК."""
    try:
        user_info = vk.method("users.get", {
            "user_ids": vk_id,
            "fields": "photo_200"
        })
        if user_info and user_info[0].get('photo_200'):
            return user_info[0]['photo_200']
    except Exception as e:
        print(f"VK avatar error: {e}")
    return None


def send(vk_user_id, text, keyboard=None, attachment=None):
    try:
        params = {
            "user_id": vk_user_id,
            "message": text,
            "random_id": get_random_id(),
        }
        if keyboard is not None:
            params["keyboard"] = keyboard.get_keyboard()
        if attachment:
            params["attachment"] = attachment
        vk.messages.send(**params)
    except Exception as e:
        print(f"Send error: {e}")


def make_main_keyboard():
    kb = VkKeyboard(one_time=False, inline=False)
    kb.add_button("💰 Баланс", color=VkKeyboardColor.PRIMARY)
    kb.add_button("➕ Добавить трату", color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("📊 График", color=VkKeyboardColor.PRIMARY)
    kb.add_button("🌐 Сайт", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("🔗 Привязать ВК", color=VkKeyboardColor.SECONDARY)
    kb.add_button("ℹ️ Помощь", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("🧹 Очистить чат", color=VkKeyboardColor.NEGATIVE)
    return kb


def make_cancel_inline():
    kb = VkKeyboard(inline=True)
    kb.add_button("⬅️ Отмена", color=VkKeyboardColor.SECONDARY)
    return kb


def delete_history(vk_user_id, count=50):
    try:
        history = vk.messages.getHistory(user_id=vk_user_id, count=count, rev=0)
        items = history.get("items", [])
        message_ids = [str(m["id"]) for m in items if m.get("out") == 1]
        if not message_ids:
            return 0
        vk.messages.delete(message_ids=",".join(message_ids), delete_for_all=1)
        return len(message_ids)
    except Exception as e:
        print(f"Delete error: {e}")
        return -1


def handle_link_result(vk_id, resp):
    if resp is None:
        send(vk_id, "⚠️ Сервер недоступен.", keyboard=make_main_keyboard())
        return
    if resp.status_code == 200:
        send(vk_id, "✅ Аккаунт привязан! Аватар загружен из ВК.", keyboard=make_main_keyboard())
        return
    if resp.status_code == 409:
        send(
            vk_id,
            "ℹ️ Этот ВК уже привязан к аккаунту на сайте.\n"
            "Если нужно привязать другой аккаунт — сначала отвяжите ВК в профиле на сайте.",
            keyboard=make_main_keyboard()
        )
        return
    try:
        err = resp.json().get('error') or resp.json().get('detail') or 'Ошибка'
    except Exception:
        err = 'Ошибка'
    send(vk_id, f"❌ {err}", keyboard=make_main_keyboard())


ALREADY_LINKED_TEXT = (
    "ℹ️ Ты уже привязан к аккаунту на сайте.\n"
    "Если хочешь привязать другой аккаунт — сначала отвяжи ВК в профиле на сайте."
)


# ============================================================
# ОБРАБОТКА
# ============================================================
while True:
    try:
        for event in longpoll.listen():
            if event.type != VkBotEventType.MESSAGE_NEW:
                continue

            touch_heartbeat()

            vk_id = event.object.message["from_id"]
            text = event.object.message.get("text", "").strip()
            print(f"[{vk_id}] {text}")

            if not text:
                continue

            low = text.lower()
            state = user_states.get(vk_id)

            # ---------- Отмена ----------
            if low in ("⬅️ отмена", "/cancel", "отмена"):
                user_states.pop(vk_id, None)
                send(vk_id, "Ок, отменил.", keyboard=make_main_keyboard())
                continue

            # ---------- Ждём трату ----------
            if state == "awaiting_expense":
                parts = text.split(maxsplit=1)
                if len(parts) != 2:
                    send(vk_id, "❌ Формат: СУММА КАТЕГОРИЯ\nНапример: 500 еда",
                         keyboard=make_cancel_inline())
                    continue
                try:
                    amount = float(parts[0].replace(",", "."))
                except ValueError:
                    send(vk_id, "❌ Сумма должна быть числом. Попробуй: 500 еда",
                         keyboard=make_cancel_inline())
                    continue
                category = parts[1].strip()
                resp = api_post("/api/add/", {
                    "vk_id": vk_id,
                    "amount": amount,
                    "category": category,
                    "type": "expense"
                })
                user_states.pop(vk_id, None)
                if resp is None:
                    send(vk_id, "⚠️ Сервер недоступен.", keyboard=make_main_keyboard())
                elif resp.status_code == 200:
                    send(vk_id, f"✅ {amount:.2f} ₽ «{category}» добавлено.",
                         keyboard=make_main_keyboard())
                else:
                    send(vk_id, "❌ Сначала привяжи аккаунт: /link КОД",
                         keyboard=make_main_keyboard())
                continue

            # ---------- Ждём код привязки ----------
            if state == "awaiting_link_code":
                code = text.strip()
                avatar_url = get_vk_avatar_url(vk_id)
                resp = api_post("/api/link/", {
                    "vk_id": vk_id,
                    "code": code,
                    "avatar_url": avatar_url
                })
                user_states.pop(vk_id, None)
                handle_link_result(vk_id, resp)
                continue

            # ---------- /start и /help ----------
            if low in ("/start", "/help", "помощь", "начать", "ℹ️ помощь"):
                send(
                    vk_id,
                    "👋 Привет! Я бот для учёта бюджета.\n\n"
                    f"🌐 Сайт: {SITE_URL}\n\n"
                    "Выбери действие на клавиатуре ниже 👇",
                    keyboard=make_main_keyboard()
                )
                continue

            # ---------- Баланс ----------
            if low in ("💰 баланс", "/balance", "баланс"):
                resp = api_post("/api/balance/", {"vk_id": vk_id})
                if resp is None:
                    send(vk_id, "⚠️ Сервер недоступен.", keyboard=make_main_keyboard())
                elif resp.status_code == 200:
                    d = resp.json()
                    send(
                        vk_id,
                        f"💰 Баланс: {d['balance']:.2f} ₽\n"
                        f"📈 Доходы: {d['income']:.2f} ₽\n"
                        f"📉 Расходы: {d['expenses']:.2f} ₽",
                        keyboard=make_main_keyboard()
                    )
                else:
                    send(vk_id, "🔗 Сначала привяжи аккаунт.", keyboard=make_main_keyboard())
                continue

            # ---------- График ----------
            if low in ("📊 график", "/chart", "график"):
                if not is_vk_linked(vk_id):
                    send(vk_id, "🔗 Сначала привяжи аккаунт.", keyboard=make_main_keyboard())
                    continue
                try:
                    import matplotlib
                    matplotlib.use('Agg')
                    import matplotlib.pyplot as plt
                except Exception as e:
                    print(f"matplotlib not available: {e}")
                    send(vk_id, "⚠️ Графики временно недоступны.", keyboard=make_main_keyboard())
                    continue

                resp = api_get("/api/transactions/", params={"vk_id": vk_id})
                if resp is None or resp.status_code != 200:
                    send(vk_id, "⚠️ Не удалось получить данные.", keyboard=make_main_keyboard())
                    continue

                data = resp.json().get("transactions", [])
                by_cat = {}
                for t in data:
                    if t.get("type") == "expense":
                        cat = t.get("category") or "Прочее"
                        by_cat[cat] = by_cat.get(cat, 0) + float(t.get("amount", 0))

                if not by_cat:
                    send(vk_id, "📭 Нет расходов для графика.", keyboard=make_main_keyboard())
                    continue

                labels = list(by_cat.keys())
                sizes = list(by_cat.values())
                fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
                colors = ['#6366f1', '#8b5cf6', '#ec4899', '#06b6d4', '#10b981',
                          '#f59e0b', '#ef4444', '#14b8a6', '#a855f7']
                ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                       colors=colors[:len(labels)], textprops={'fontsize': 10})
                ax.set_title("Расходы по категориям", fontsize=13, fontweight='bold')
                path = f"/tmp/chart_{vk_id}_{int(time.time())}.png"
                fig.savefig(path, bbox_inches='tight', facecolor='white')
                plt.close(fig)

                try:
                    upload_url = vk.photos.getMessagesUploadServer(peer_id=vk_id)["upload_url"]
                    with open(path, "rb") as f:
                        files = {"photo": ("chart.png", f, "image/png")}
                        upload_resp = requests.post(upload_url, files=files, timeout=15).json()
                    saved = vk.photos.saveMessagesPhoto(
                        photo=upload_resp["photo"],
                        server=upload_resp["server"],
                        hash=upload_resp["hash"]
                    )[0]
                    attachment = f"photo{saved['owner_id']}_{saved['id']}"
                    send(vk_id, "📊 Твои расходы по категориям:", attachment=attachment,
                         keyboard=make_main_keyboard())
                except Exception as e:
                    print(f"Chart upload error: {e}")
                    send(vk_id, "⚠️ Не удалось отправить график.", keyboard=make_main_keyboard())
                finally:
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                continue

            # ---------- Сайт ----------
            if low in ("🌐 сайт", "/site", "сайт"):
                send(
                    vk_id,
                    f"🌐 Открыть сайт:\n{SITE_URL}\n\n"
                    "Там графики, аналитика и управление бюджетом.",
                    keyboard=make_main_keyboard()
                )
                continue

            # ---------- Привязка: кнопка ----------
            if low in ("🔗 привязать вк", "/link", "привязать"):
                if is_vk_linked(vk_id):
                    send(vk_id, ALREADY_LINKED_TEXT, keyboard=make_main_keyboard())
                    continue
                user_states[vk_id] = "awaiting_link_code"
                send(
                    vk_id,
                    "🔗 Зайди на сайт → Профиль → Привязать ВК → получи код.\n"
                    "Потом отправь код сюда одним сообщением (без /link).",
                    keyboard=make_cancel_inline()
                )
                continue

            # ---------- Привязка: /link КОД ----------
            if low.startswith("/link "):
                if is_vk_linked(vk_id):
                    send(vk_id, ALREADY_LINKED_TEXT, keyboard=make_main_keyboard())
                    continue
                code = text[6:].strip()
                avatar_url = get_vk_avatar_url(vk_id)
                resp = api_post("/api/link/", {
                    "vk_id": vk_id,
                    "code": code,
                    "avatar_url": avatar_url
                })
                handle_link_result(vk_id, resp)
                continue

            # ---------- Добавить трату ----------
            if low in ("➕ добавить трату", "/add", "добавить"):
                user_states[vk_id] = "awaiting_expense"
                send(
                    vk_id,
                    "➕ Напиши трату в формате:\n\n"
                    "   СУММА КАТЕГОРИЯ\n\n"
                    "Например: 500 еда",
                    keyboard=make_cancel_inline()
                )
                continue

            # ---------- Очистить чат ----------
            if low in ("🧹 очистить чат", "/clear", "очистить"):
                send(vk_id, "🧹 Удаляю сообщения...", keyboard=make_main_keyboard())
                deleted = delete_history(vk_id, count=50)
                if deleted > 0:
                    send(vk_id, f"✅ Удалено: {deleted}", keyboard=make_main_keyboard())
                elif deleted == 0:
                    send(vk_id, "🤷 Нечего удалять.", keyboard=make_main_keyboard())
                else:
                    send(vk_id, "⚠️ Не удалось удалить.", keyboard=make_main_keyboard())
                continue

            # ---------- Неизвестная команда ----------
            send(vk_id, "❓ Не понял. Используй кнопки ниже 👇", keyboard=make_main_keyboard())

    except Exception as e:
        print(f"Ошибка соединения с VK: {e}. Переподключение через 30 секунд...")
        time.sleep(30)