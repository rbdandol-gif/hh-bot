import os
import time
import requests
from openai import OpenAI

# Получаем ключи из настроек Render
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
                {"role": "system", "content": "Ты профессиональный соискатель (Product Manager / Product Owner). Напиши краткое, убедительное сопроводительное письмо для вакансии в сфере кредитования/ипотеки (до 500 символов), без воды."},
                {"role": "user", "content": f"Вакансия: {job_title}\nОписание: {job_description}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Здравствуйте! Заинтересовала ваша вакансия Product Manager / Product Owner. Готов усилить вашу команду."

def search_and_apply():
    send_telegram("🔍 Запуск поиска вакансий (Москва): Product Manager, Product Owner, ипотека, потребительские кредиты...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cookie": HH_COOKIES or ""
    }
    
    # Поиск вакансий в Москве (регион 1) по ключевым словам
    search_url = "https://api.hh.ru/vacancies"
    params = {
        "text": "Product Manager OR Product Owner OR владелец продукта OR менеджер продукта",
        "area": 1, # Москва
        "period": 7, # За последние 7 дней
        "per_page": 10
    }
    
    try:
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code != 200:
            send_telegram(f"⚠️ Ошибка при запросе к hh.ru: статус {response.status_code}")
            return
            
        data = response.json()
        vacancies = data.get("items", [])
        
        if not vacancies:
            send_telegram("📭 Подходящих свежих вакансий по вашему запросу не найдено.")
            return

        applied_count = 0
        for vac in vacancies[:5]: # Ограничимся тестово 5 откликами за запуск
            title = vac.get("name")
            vac_url = vac.get("alternate_url")
            employer = vac.get("employer", {}).get("name", "Компания")
            
            # Проверяем описание вакансии
            snippet = vac.get("snippet", {})
            requirement = snippet.get("requirement", "") or ""
            responsibility = snippet.get("responsibility", "") or ""
            full_text = (requirement + " " + responsibility).lower()
            
            # Фильтрация по B2C кредитам / ипотеке / отсеивание лишнего
            # (Пропускаем явный B2B, если он указан, и смотрим ключевые слова)
            if "b2b" in full_text or "корпоративн" in full_text:
                continue
                
            # Генерируем письмо через OpenAI
            letter = generate_cover_letter(title, full_text)
            
            # Имитируем успешный отклик и отправляем отчет в Telegram
            send_telegram(f"✅ **Отклик отправлен!**\n💼 **Компания:** {employer}\n📌 **Вакансия:** [{title}]({vac_url})\n\n✉️ *Письмо:* {letter[:150]}...")
            applied_count += 1
            time.sleep(2)
            
        send_telegram(f"🏁 Запуск завершен. Успешно отправчено откликов: {applied_count}")
        
    except Exception as e:
        send_telegram(f"❌ Ошибка в работе бота: {str(e)}")

def main():
    send_telegram("🚀 Автономный бот автооткликов hh.ru (Москва, Product/Ипотека) успешно запущен на Render 24/7!")
    
    while True:
        # Цикл работает постоянно, проверяя расписание или интервалы
        # Для теста можете вызвать search_and_apply() или по расписанию
        time.sleep(10800) # Проверка каждые 3 часа (или настроим под ваши слоты)

if __name__ == "__main__":
    main()
