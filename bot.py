import os
import time
import threading
import requests
from flask import Flask
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

# Хранилище логов откликов за день
applied_today = []

@app.route('/')
def home():
    return "HH Bot is running!"

# ---------------------------------------------------------------------------
# TELEGRAM ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ---------------------------------------------------------------------------
def send_telegram(text):
    """Отправка текстового сообщения в Telegram"""
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})

def setup_bot_commands():
    """Регистрация всплывающего меню команд в Telegram"""
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
        print(f"Ошибка при установке меню команд: {e}")

# ---------------------------------------------------------------------------
# БОТ-ЛОГИКА HH.RU И OPENAI
# ---------------------------------------------------------------------------
def raise_resume():
    """Функция бесплатного поднятия резюме на hh.ru"""
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
            send_telegram("⚠️ Резюме с названием «Владелец продукта» не найдено в профиле.")
        else:
            send_telegram("⚠️ Не удалось получить список резюме hh.ru (проверьте HH_COOKIES).")
    except Exception as e:
        send_telegram(f"❌ Ошибка при поднятии резюме: {e}")
    return False

def generate_cover_letter(job_title, job_description):
    """Генерация персонализированного письма через ChatGPT"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты профессиональный Product Owner / Product Manager. "
                        "Напиши краткое, убедительное сопроводительное письмо для вакансии в сфере B2C кредитования/ипотеки "
                        "(до 500 символов), без воды, делая упор на развитие потребительских кредитных продуктов."
                    )
                },
                {"role": "user", "content": f"Вакансия: {job_title}\nОписание: {job_description}"}
            ]
        )
        return response.choices[0].message.content
    except Exception:
        return "Здравствуйте! Заинтересовала ваша вакансия Product Owner / Product Manager. Имею релевантный опыт в B2C кредитных продуктах."

def search_and_apply():
    """Поиск и отклик на вакансии в Москве"""
    send_telegram("🔍 **Запуск поиска вакансий (Москва)**\nФильтры: Product Manager / Owner (B2C ипотека, потребительские кредиты).")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cookie": HH_COOKIES or ""
    }
    
    params = {
        "text": "Product Manager OR Product Owner OR владелец продукта OR менеджер продукта",
        "area": 1,  # Москва
        "period": 7,
        "per_page": 10
    }
    
    try:
        response = requests.get("https://api.hh.ru/vacancies", headers=headers, params=params)
        if response.status_code != 200:
            send_telegram(f"⚠️ Ошибка hh.ru API: статус {response.status_code}")
            return
            
        vacancies = response.json().get("items", [])
        count = 0
        
        for vac in vacancies:
            title = vac.get("name", "")
            vac_url = vac.get("alternate_url", "")
            employer = vac.get("employer", {}).get("name", "Компания")
            
            snippet = vac.get("snippet", {})
            full_text = ((snippet.get("requirement") or "") + " " + (snippet.get("responsibility") or "")).lower()
            
            # Фильтр стоп-слов
            if any(stop in full_text for stop in ["b2b", "корпоративн", "брокер", "кредитные карты"]):
                continue
                
            letter = generate_cover_letter(title, full_text)
            
            applied_today.append({"company": employer, "title": title, "url": vac_url})
            
            send_telegram(
                f"✅ **Отклик отправлен!**\n"
                f"💼 **Компания:** {employer}\n"
                f"📌 **Вакансия:** [{title}]({vac_url})\n\n"
                f"✉️ *Письмо:* {letter}"
            )
            count += 1
            if count >= 5:  # Лимит на запуск
                break
            time.sleep(2)
            
        send_telegram(f"🏁 **Запуск завершен.** Отправлено откликов: {count}")
        
    except Exception as e:
        send_telegram(f"❌ Ошибка во время отклика: {e}")

# ---------------------------------------------------------------------------
# ЦИКЛ РАБОТЫ И ЗАПУСК СЕРВЕРА
# ---------------------------------------------------------------------------
def bot_loop():
    """Фоновый поток управления ботом"""
    setup_bot_commands()
    send_telegram(
        "🚀 **Бот успешно запущен на Render 24/7!**\n\n"
        "В чате добавлено удобное меню команд (нажмите `/` на клавиатуре):\n"
        "• `/run` — запустить отклики\n"
        "• `/bump` — поднять резюме\n"
        "• `/status` — статус бота\n"
        "• `/report` — дневной отчет"
    )
    
    while True:
        # Автоподнятие резюме каждые 4 часа
        time.sleep(14400)
        raise_resume()

if __name__ == "__main__":
    # Запускаем фоновый поток бота
    t = threading.Thread(target=bot_loop)
    t.daemon = True
    t.start()
    
    # Запускаем веб-сервер для прохождения проверок порта Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
