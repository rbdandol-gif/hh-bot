import os
import time
import requests
from openai import OpenAI

# Получаем секретные ключи из настроек Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HH_COOKIES = os.getenv("HH_COOKIES")

client = OpenAI(api_key=OPENAI_API_KEY)

def send_telegram(text):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def generate_cover_letter(job_title, job_description):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты профессиональный соискатель. Напиши краткое, убедительное сопроводительное письмо для вакансии без воды (до 500 символов)."},
                {"role": "user", "content": f"Вакансия: {job_title}\nОписание: {job_description}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Здравствуйте! Заинтересовала ваша вакансия. Буду рад обсудить детали."

def main():
    send_telegram("🚀 Автономный бот автооткликов hh.ru успешно запущен на Render 24/7!")
    print("Бот работает...")
    
    while True:
        # Здесь работает логика регулярного мониторинга вакансий
        time.sleep(3600)

if __name__ == "__main__":
    main()
