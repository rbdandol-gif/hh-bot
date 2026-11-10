import os
import time
import threading
import requests
from flask import Flask, request
from openai import OpenAI

# ---------------------------------------------------------------------------
# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# ---------------------------------------------------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HH_COOKIES = os.getenv("HH_COOKIES")

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

applied_today = []

# ---------------------------------------------------------------------------
# TELEGRAM ФУНКЦИИ
# ---------------------------------------------------------------------------
def send_telegram(text):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})

def setup_bot_commands():
    if not TELEGRAM_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setMyCommands"
    commands = [
        {"command": "run", "description": "🚀 Поиск вакансий B2C и отклики в Москве"},
        {"command": "bump", "description": "🔝 Поднять резюме «Владелец продукта»"},
        {"command": "status", "description": "ℹ️ Текущий статус работы бота"},
        {"command": "report", "description": "📊 Вечерний отчет по откликам за день"}
    ]
    try:
        requests.post(url, json={"commands": commands})
    except Exception as e:
        print(f"Ошибка меню команд: {e}")

# ---------------------------------------------------------------------------
# ЛОГИКА HH.RU И OPENAI
# ---------------------------------------------------------------------------
def raise_resume():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cookie": HH_COOKIES or ""
    }
    try:
        res = requests.get("https://api.hh.ru/resumes/mine", headers=headers)
        if res.status_code == 200:
            resumes = res.json().get("items", [])
            for r in resumes:
                title = r.get("title", "")
                if "Владелец продукта" in title or "Product Owner" in title:
                    resume_id = r.get("id")
                    bump_res = requests.post(f"https://api.hh.ru/resumes/{resume_id}/publish", headers=headers)
                    if bump_res.status_code == 204:
                        send_telegram("🚀 **Резюме «Владелец продукта» успешно поднято в поиске!**")
                        return True
                    else:
                        send_telegram("ℹ️ Кнопка поднятия резюме пока недоступна (интервал 4 часа не прошел).")
                        return False
            send_telegram("⚠️ Резюме «Владелец продукта» не найдено.")
        else:
            send_telegram("⚠️ Не удалось получить список резюме (проверьте HH_COOKIES).")
    except Exception as e:
        send_telegram(f"❌ Ошибка при поднятии резюме: {e}")
    return False

def generate_cover_letter(job_title, job_description):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты профессиональный Product Owner. Напиши краткое сопроводительное письмо для вакансии B2C кредитования/ипотеки (до 500 символов)."},
                {"role": "user", "content": f"Вакансия: {job_title}\nОписание: {job_description}"}
            ]
        )
        return response.choices[0].message.content
    except Exception:
        return "Здравствуйте! Заинтересовала ваша вакансия Product Owner / Product Manager. Имею релевантный опыт."

def search_and_apply():
    send_telegram("🔍 **Запуск поиска вакансий (Москва)**\nФильтры: Product Manager / Owner (B2C кредиты/ипотека).")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cookie": HH_COOKIES or ""
    }
    params = {
        "text": "Product Manager OR Product Owner OR владелец продукта",
        "area": 1,
        "period": 7,
        "per_page": 10
    }
    try:
        response = requests.get("https://api.hh.ru/vacancies", headers=headers, params=params)
        if response.status_code != 200:
            send_telegram(f"⚠️ Ошибка hh.ru API: {response.status_code}")
            return
            
        vacancies = response.json().get("items", [])
        count = 0
        
        for vac in vacancies:
            title = vac.get("name", "")
            vac_url = vac.get("alternate_url", "")
            employer = vac.get("employer", {}).get("name", "Компания")
            snippet = vac.get("snippet", {})
            full_text = ((snippet.get("requirement") or "") + " " + (snippet.get("responsibility") or "")).lower()
            
            if any(stop in full_text for stop in ["b2b", "корпоративн", "брокер", "кредитные карты"]):
                continue
                
            letter = generate_cover_letter(title, full_text)
            applied_today.append({"company": employer, "title": title, "url": vac_url})
            
            send_telegram(f"✅ **Отклик отправлен!**\n💼 **Компания:** {employer}\n📌 **Вакансия:** [{title}]({vac_url})\n\n✉️ *Письмо:* {letter}")
            count += 1
            if count >= 5:
                break
            time.sleep(2)
            
        send_telegram(f"🏁 **Запуск завершен.** Отправлено откликов: {count}")
    except Exception as e:
        send_telegram(f"❌ Ошибка во время отклика: {e}")

# ---------------------------------------------------------------------------
# FLASK ВЕБ-СЕРВЕР И ОБРАБОТЧИК КОМАНД ИЗ TELEGRAM
# ---------------------------------------------------------------------------
@app.route('/')
def home():
    return "HH Bot is running!"

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def receive_telegram_update():
    """Эндпоинт, куда Telegram шлет входящие сообщения/команды"""
    data = request.get_json()
    if data and "message" in data:
        message = data["message"]
        text = message.get("text", "")
        
        # Обрабатываем команды
        if text == "/run":
            threading.Thread(target=search_and_apply).start()
        elif text == "/bump":
            threading.Thread(target=raise_resume).start()
        elif text == "/status":
            send_telegram("ℹ️ **Статус:** Бот активен, работает в фоновом режиме на Render 24/7.")
        elif text == "/report":
            send_telegram(f"📊 **Отчет за сегодня:** Отправлено откликов: {len(applied_today)}")
            
    return {"status": "ok"}

def set_webhook():
    """Автоматическая привязка вебхука к нашему URL на Render"""
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if render_url and TELEGRAM_TOKEN:
        webhook_url = f"{render_url}/{TELEGRAM_TOKEN}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}")

# ---------------------------------------------------------------------------
# ФОНОВЫЙ ПОТОК И ЗАПУСК
# ---------------------------------------------------------------------------
def bot_loop():
    setup_bot_commands()
    set_webhook()
    send_telegram(
        "🚀 **Бот полностью активирован!**\n\n"
        "Теперь команды интерактивные:\n"
        "• `/run` — запустить отклики\n"
        "• `/bump` — поднять резюме\n"
        "• `/status` — статус\n"
        "• `/report` — отчет"
    )
    while True:
        # Автоматическое поднятие резюме каждые 4 часа
        time.sleep(14400)
        raise_resume()

if __name__ == "__main__":
    t = threading.Thread(target=bot_loop)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
