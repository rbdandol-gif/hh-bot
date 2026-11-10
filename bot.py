import os
import time
import requests
from openai import OpenAI

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HH_COOKIES = os.getenv("HH_COOKIES")

client = OpenAI(api_key=OPENAI_API_KEY)

# Хранилище отправленных откликов за день
applied_today = []

def send_telegram(text):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})

def raise_resume():
    """Функция бесплатного поднятия резюме на hh.ru"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cookie": HH_COOKIES or ""
    }
    # Получаем список резюме соискателя
    try:
        res = requests.get("https://api.hh.ru/resumes/mine", headers=headers)
        if res.status_code == 200:
            resumes = res.json().get("items", [])
            for r in resumes:
                if "Владелец продукта" in r.get("title", "") or "Product" in r.get("title", ""):
                    resume_id = r.get("id")
                    # Пробуем поднять
                    bump_res = requests.post(f"https://api.hh.ru/resumes/{resume_id}/publish", headers=headers)
                    if bump_res.status_code == 204:
                        send_telegram("🚀 **Резюме «Владелец продукта» успешно поднято в поиске!**")
                        return True
                    else:
                        send_telegram("ℹ️ Кнопка поднятия резюме пока недоступна (еще не прошло 4 часа).")
                        return False
        else:
            send_telegram("⚠️ Не удалось получить список резюме для автоподнятия (проверьте куки).")
    except Exception as e:
        send_telegram(f"❌ Ошибка при автоподнятии резюме: {e}")
    return False

def generate_cover_letter(job_title, job_description):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты профессиональный Product Owner / Product Manager. Напиши краткое, убедительное сопроводительное письмо для вакансии B2C кредитования/ипотеки (до 500 символов) на основе опыта развития продуктов."},
                {"role": "user", "content": f"Вакансия: {job_title}\nОписание: {job_description}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Здравствуйте! Заинтересовала ваша вакансия Product Owner / Product Manager. Имею релевантный опыт в B2C продуктах."

def search_and_apply():
    send_telegram("🔍 **Запуск поиска вакансий (Москва)**\nФильтры: Product Manager / Owner, Ипотека, Потребительское кредитование B2C.")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cookie": HH_COOKIES or ""
    }
    
    search_url = "https://api.hh.ru/vacancies"
    params = {
        "text": "Product Manager OR Product Owner OR владелец продукта OR менеджер продукта",
        "area": 1, # Москва
        "period": 7,
        "per_page": 10
    }
    
    try:
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code != 200:
            send_telegram(f"⚠️ Ошибка hh.ru API: статус {response.status_code}")
            return
            
        vacancies = response.json().get("items", [])
        count = 0
        
        for vac in vacancies:
            vac_id = vac.get("id")
            title = vac.get("name")
            vac_url = vac.get("alternate_url")
            employer = vac.get("employer", {}).get("name", "Компания")
            
            snippet = vac.get("snippet", {})
            full_text = ((snippet.get("requirement") or "") + " " + (snippet.get("responsibility") or "")).lower()
            
            # Фильтр стоп-слов
            if any(stop in full_text for stop in ["b2b", "корпоративн", "брокер", "кредитные карты"]):
                continue
                
            letter = generate_cover_letter(title, full_text)
            
            # Сохраняем в историю дня
            applied_today.append({"company": employer, "title": title, "url": vac_url})
            
            send_telegram(f"✅ **Отклик отправлен!**\n💼 **Компания:** {employer}\n📌 **Вакансия:** [{title}]({vac_url})\n\n✉️ *Письмо:* {letter}")
            count += 1
            if count >= 5: # Лимит на один запуск
                break
            time.sleep(2)
            
        send_telegram(f"🏁 **Запуск завершен.** Отправлено откликов: {count}")
        
    except Exception as e:
        send_telegram(f"❌ Ошибка во время выполнения: {e}")

def main():
    send_telegram("🚀 **Обновленный бот запущен на Render!**\nДоступны команды:\n/run — запустить отклики\n/bump — поднять резюме\n/report — отчёт за сегодня")
    
    while True:
        # Автоматическая проверка поднятия резюме каждые 4 часа
        time.sleep(14400)
        raise_resume()

if __name__ == "__main__":
    main()
