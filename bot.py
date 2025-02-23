import logging
import asyncio
import requests
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Телеграм токен
TOKEN = "8045856936:AAGUsvT_VBd-aj8P_g49qo2jsXliuXUbR5w"

# OpenSanctions API ключ (беремо з середовищних змінних для безпеки)
API_KEY = "ee37de2e10cbcfe69c8a659caf465891"
API_URL = "https://api.opensanctions.org"
RNBO_API_URL = "https://api-drs.nsdc.gov.ua/sanctions-registry/subjects"

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота та диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Функція для перевірки санкційного списку через OpenSanctions API та РНБО
async def check_sanctions(name):
    session = requests.Session()
    session.headers['Authorization'] = f'ApiKey {API_KEY}'
    session.headers['Content-Type'] = 'application/json'
    
    results = ["🔍 Перевірка санкційних списків:" ]
    file_content = "Ім'я, Санкційний список\n"

    try:
        # Запит до OpenSanctions API
        response = session.get(f"{API_URL}/search/default?q={name}&api_key={API_KEY}")
        response.raise_for_status()
        data = response.json()

        entities = data.get("results", [])
        if entities:
            results.append("✅ Знайдено у OpenSanctions:")
            for entity in entities:
                entity_name = entity.get("caption", "❓ Невідоме ім'я")
                sanction_list = entity.get("datasets", ["Невідомий список"])
                formatted_list = ", ".join(sanction_list) if isinstance(sanction_list, list) else sanction_list
                results.append(f"🔹 {entity_name} – 📄 {formatted_list}")
                file_content += f"{entity_name}, {formatted_list}\n"
        else:
            results.append("❌ Не знайдено у OpenSanctions.")

    except requests.exceptions.RequestException as e:
        results.append(f"⚠️ Помилка OpenSanctions API: {e}")
    
    try:
        # Запит до бази санкцій РНБО
        rnbo_response = requests.get(f"{RNBO_API_URL}?last_name={name}&type=individual")
        rnbo_response.raise_for_status()
        rnbo_data = rnbo_response.json()
        
        if rnbo_data.get("data"):
            results.append("✅ Знайдено у санкційних списках РНБО:")
            for person in rnbo_data.get("data", []):
                full_name = person.get("full_name", "❓ Невідоме ім'я")
                sanction_start = person.get("sanction_start_date", "❓ Дата відсутня")
                results.append(f"🔹 {full_name} – 🗓 Дата санкцій: {sanction_start}")
                file_content += f"{full_name}, {sanction_start}\n"
        else:
            results.append("❌ Не знайдено у санкціях РНБО.")

    except requests.exceptions.RequestException as e:
        results.append(f"⚠️ Помилка отримання даних з санкційної бази РНБО: {e}")

    # Збереження результатів у файл
    file_path = "sanctions_check.csv"
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_content)

    return "\n".join(results), file_path

# Обробник команди /start
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer("Вітаю! Введіть прізвище особи для перевірки у санкційних списках.")

# Обробник введеного тексту (прізвище)
@dp.message()
async def handle_name(message: types.Message):
    name = message.text.strip()
    result, file_path = await check_sanctions(name)
    
    if file_path:
        await message.answer(result)
        await message.answer_document(types.FSInputFile(file_path), caption="📄 Повний список збігів")
    else:
        await message.answer(result)

# Основна функція для запуску бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
