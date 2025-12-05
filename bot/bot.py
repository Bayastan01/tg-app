import asyncio
import logging
import sys
import os
import re
import json
import html
from datetime import datetime
from typing import Dict, Optional
import aiohttp

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flower_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === ВАШИ ДАННЫЕ ===
BOT_TOKEN = "8299558870:AAEAVbDQIgFi2F3sjcfy8g2Win5McImcGaQ"
ADMIN_ID = 6174995259
CHANNEL_ID = "-1003393988300"
PRICE = 50
WEB_APP_URL = "https://ваш-сайт.vercel.app"  # ЗАМЕНИ НА СВОЙ URL С VERCEL!

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, Location
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Файл для хранения данных
STORAGE_FILE = "user_requests.json"

def load_user_data() -> Dict[int, Dict]:
    """Загрузка данных из файла"""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            return {}
    return {}

def save_user_data():
    """Сохранение данных в файл"""
    try:
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")

# Хранилище данных
user_data = load_user_data()

# ==================== КЛАВИАТУРЫ ====================

def main_menu():
    """Главное меню с Web App кнопкой"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌸 Создать объявление", web_app=WebAppInfo(url=WEB_APP_URL))],
            [KeyboardButton(text="💳 Реквизиты"), KeyboardButton(text="📞 Поддержка")],
            [KeyboardButton(text="📱 Классический режим")]
        ],
        resize_keyboard=True
    )

def classic_mode_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Создать пост")],
            [KeyboardButton(text="🔙 Назад в меню")]
        ],
        resize_keyboard=True
    )

def contact_type_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Телефон")],
            [KeyboardButton(text="📞 Telegram (авто)")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

def location_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="🏙️ Ввести город/район")],
            [KeyboardButton(text="🚫 Без локации")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

def preview_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Опубликовать")],
            [KeyboardButton(text="✏️ Редактировать")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

def get_admin_keyboard(user_id: int):
    """Клавиатура для админа"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
            ]
        ]
    )

# ==================== ОСНОВНОЙ КОД ====================

@dp.message(Command("start"))
async def start_command(message: Message):
    """Команда /start"""
    user_id = message.from_user.id
    logger.info(f"START от {user_id}")
    
    welcome = f"""
<b>🌸 Добро пожаловать в Flower Market Bot!</b>

💰 <b>Стоимость публикации:</b> {PRICE} сом

✨ <b>Доступные способы создания объявлений:</b>

<b>1. 🌐 Веб-приложение (рекомендуется)</b>
• Удобная форма заполнения
• Автоматическое определение местоположения
• Предпросмотр перед отправкой

<b>2. 📱 Классический режим</b>
• Пошаговое создание через чат
• Поддержка геолокации

💳 <b>Для оплаты:</b>
• O!Money: <code>+996 707 770 740</code>
• MegaPay: <code>+996 707 770 740</code>

👇 <b>Выберите способ:</b>
"""
    
    await message.answer(welcome, parse_mode="HTML", reply_markup=main_menu())

@dp.message(F.text == "📱 Классический режим")
async def classic_mode(message: Message):
    """Переход в классический режим"""
    await message.answer(
        "<b>📱 Классический режим</b>\n\n"
        "В этом режиме вы создаете объявление по шагам через чат.\n\n"
        "Вы можете:\n"
        "• Отправлять несколько фото\n"
        "• Указать описание и цену\n"
        "• Выбрать тип контактов\n"
        "• Указать локацию на карте\n\n"
        "<b>Начнем?</b>",
        parse_mode="HTML",
        reply_markup=classic_mode_menu()
    )

@dp.message(F.text == "📝 Создать пост")
async def create_classic_post(message: Message):
    """Начало создания поста в классическом режиме"""
    user_id = message.from_user.id
    user_data[user_id] = {
        "step": "waiting_photos",
        "mode": "classic",
        "photos": [],
        "description": "",
        "price": "",
        "contacts": "",
        "location": "",
        "contact_type": "telegram"
    }
    save_user_data()
    
    await message.answer(
        "<b>📸 Шаг 1: Загрузите фото</b>\n\n"
        "Отправьте фото цветов.\n"
        "Вы можете отправить несколько фото (до 10).\n\n"
        "<i>Когда закончите, отправьте текст: </i><code>готово</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(F.text == "🔙 Назад")
async def back_command(message: Message):
    """Обработка кнопки 'Назад'"""
    user_id = message.from_user.id
    
    if user_id not in user_data:
        await message.answer("Возвращаюсь в главное меню...", reply_markup=main_menu())
        return
    
    data = user_data[user_id]
    step = data.get("step")
    
    if step == "waiting_photos":
        await message.answer("Возвращаюсь в меню...", reply_markup=classic_mode_menu())
        del user_data[user_id]
        save_user_data()
    
    elif step == "description":
        data["step"] = "waiting_photos"
        save_user_data()
        await message.answer(
            "<b>📸 Шаг 1: Загрузите фото</b>\n\n"
            "Продолжайте отправлять фото или напишите <code>готово</code>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔙 Назад")]],
                resize_keyboard=True
            )
        )
    
    elif step == "price":
        data["step"] = "description"
        save_user_data()
        await message.answer(
            "<b>📝 Шаг 2: Описание</b>\n\n"
            "Напишите описание товара:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔙 Назад")]],
                resize_keyboard=True
            )
        )
    
    elif step == "contact_type":
        data["step"] = "price"
        save_user_data()
        await message.answer(
            "<b>💰 Шаг 3: Цена</b>\n\n"
            "Укажите цену:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔙 Назад")]],
                resize_keyboard=True
            )
        )
    
    elif step == "contact_value":
        data["step"] = "contact_type"
        save_user_data()
        await message.answer(
            "<b>📞 Шаг 4: Контакты</b>\n\n"
            "Выберите тип контактов:",
            parse_mode="HTML",
            reply_markup=contact_type_menu()
        )
    
    elif step == "location_choice":
        data["step"] = "contact_value"
        save_user_data()
        phone_value = data.get('contacts', '')
        await message.answer(
            f"<b>📞 Шаг 5: Контакты</b>\n\n"
            f"Ваши контакты: {phone_value}\n"
            "Если нужно изменить, введите новые контакты:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔙 Назад")]],
                resize_keyboard=True
            )
        )
    
    elif step == "location_value":
        data["step"] = "location_choice"
        save_user_data()
        await message.answer(
            "<b>📍 Шаг 6: Локация</b>\n\n"
            "Выберите способ указания локации:",
            parse_mode="HTML",
            reply_markup=location_menu()
        )
    
    elif step == "preview":
        data["step"] = "location_value" if data.get("location") else "location_choice"
        save_user_data()
        await message.answer(
            "<b>📍 Шаг 6: Локация</b>\n\n"
            "Введите адрес или нажмите 'Без локации':",
            parse_mode="HTML",
            reply_markup=location_menu()
        )
    
    else:
        await message.answer("Возвращаюсь в меню...", reply_markup=main_menu())

@dp.message(F.text == "🔙 Назад в меню")
async def back_to_menu(message: Message):
    """Возврат в главное меню"""
    user_id = message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
        save_user_data()
    await message.answer("Возвращаюсь в главное меню...", reply_markup=main_menu())

@dp.message(F.photo)
async def handle_photo(message: Message):
    """Обработка фото"""
    user_id = message.from_user.id
    
    if user_id not in user_data:
        await message.answer("Отправьте /start для начала работы", reply_markup=main_menu())
        return
    
    data = user_data[user_id]
    step = data.get("step")
    
    # Скриншот оплаты
    if step == "waiting_payment":
        await process_payment_screenshot(message, message.photo[-1].file_id)
        return
    
    # Фото товара в классическом режиме
    if step == "waiting_photos":
        if "photos" not in data:
            data["photos"] = []
        
        # Проверяем лимит фото
        if len(data["photos"]) >= 10:
            await message.answer("⚠️ <b>Достигнут лимит фото (10)</b>\nНапишите <code>готово</code> чтобы продолжить", 
                               parse_mode="HTML")
            return
        
        # Добавляем фото
        photo_id = message.photo[-1].file_id
        data["photos"].append(photo_id)
        save_user_data()
        
        count = len(data["photos"])
        await message.answer(f"✅ <b>Фото {count} добавлено</b>\n\n"
                            f"Всего фото: {count}\n"
                            f"Можно добавить еще: {10 - count}\n\n"
                            f"<i>Когда закончите, напишите </i><code>готово</code>",
                            parse_mode="HTML")
        return
    
    await message.answer("Сейчас не время отправлять фото. Следуйте инструкциям.")

@dp.message(F.text == "готово")
async def handle_done_photos(message: Message):
    """Завершение загрузки фото"""
    user_id = message.from_user.id
    
    if user_id not in user_data:
        return
    
    data = user_data[user_id]
    step = data.get("step")
    
    if step != "waiting_photos":
        return
    
    if not data.get("photos"):
        await message.answer("❌ <b>Нет загруженных фото</b>\n\n"
                           "Сначала отправьте хотя бы одно фото",
                           parse_mode="HTML")
        return
    
    data["step"] = "description"
    save_user_data()
    
    await message.answer(
        "<b>📝 Шаг 2: Описание</b>\n\n"
        "Напишите подробное описание товара:\n\n"
        "<i>Пример:</i>\n"
        "Букет из 101 белой розы — символ чистой и бесконечной любви. "
        "Идеально подходит для особых случаев: свадьбы, годовщины, предложения руки и сердца.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )

@dp.message(F.text == "💳 Реквизиты")
async def show_payment_info(message: Message):
    """Показать реквизиты оплаты"""
    await message.answer(
        f"""
<b>💳 Реквизиты для оплаты</b>

💰 <b>Стоимость публикации:</b> {PRICE} сом

<b>O!Money:</b> <code>+996 707 770 740</code>
<b>MegaPay:</b> <code>+996 707 770 740</code>

📎 <b>После создания объявления и оплаты отправьте скриншот чека.</b>

⏱ <b>Время обработки:</b> 10-30 минут после оплаты

<b>⚠️ Важно:</b> Оплата производится только после создания и проверки объявления.
""",
        parse_mode="HTML"
    )

@dp.message(F.text == "📞 Поддержка")
async def show_support(message: Message):
    """Показать информацию о поддержке"""
    await message.answer(
        "<b>📞 Поддержка</b>\n\n"
        "По всем вопросам обращайтесь к администратору:\n"
        "<b>@admin</b>\n\n"
        "⏰ <b>Время работы поддержки:</b>\n"
        "Пн-Пт: 9:00-18:00\n"
        "Сб-Вс: 10:00-16:00\n\n"
        "💬 <b>Чат поддержки:</b> @flower_support_chat",
        parse_mode="HTML"
    )

@dp.message(F.location)
async def handle_location(message: Message):
    """Обработка геолокации"""
    user_id = message.from_user.id
    
    if user_id not in user_data:
        await message.answer("❌ Сначала создайте объявление!")
        return
    
    data = user_data[user_id]
    step = data.get("step")
    
    if step == "location_value":
        # Получаем адрес по координатам
        location = message.location
        address = await get_address_from_coords(location.latitude, location.longitude)
        
        data["location"] = {
            "type": "coordinates",
            "latitude": location.latitude,
            "longitude": location.longitude,
            "address": address or f"{location.latitude}, {location.longitude}"
        }
        data["step"] = "preview"
        save_user_data()
        
        if address:
            await message.answer(f"✅ <b>Локация определена!</b>\n\n"
                               f"📍 <b>Адрес:</b> {address}\n"
                               f"📌 <b>Координаты:</b> {location.latitude}, {location.longitude}",
                               parse_mode="HTML")
        else:
            await message.answer(f"✅ <b>Геолокация получена!</b>\n\n"
                               f"📍 <b>Координаты:</b> {location.latitude}, {location.longitude}",
                               parse_mode="HTML")
        
        await show_preview(message, data)
    else:
        await message.answer("❌ Сейчас не время отправлять локацию. Следуйте инструкциям.")

async def get_address_from_coords(lat: float, lon: float) -> Optional[str]:
    """Получает адрес по координатам через Nominatim"""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        headers = {
            'User-Agent': 'FlowerMarketBot/1.0'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    address = data.get('display_name', '')
                    
                    # Упрощаем адрес
                    if 'address' in data:
                        addr = data['address']
                        components = []
                        
                        if 'city' in addr:
                            components.append(f"г. {addr['city']}")
                        elif 'town' in addr:
                            components.append(f"г. {addr['town']}")
                        elif 'village' in addr:
                            components.append(f"с. {addr['village']}")
                        
                        if 'road' in addr:
                            components.append(f"ул. {addr['road']}")
                        
                        if 'house_number' in addr:
                            components.append(f"д. {addr['house_number']}")
                        
                        if components:
                            return ", ".join(components)
                    
                    return address[:200]  # Ограничиваем длину
    except Exception as e:
        logger.error(f"Ошибка получения адреса: {e}")
        return None

@dp.message(F.text)
async def handle_text(message: Message):
    """Обработка текста в классическом режиме"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Основные команды меню
    if user_id not in user_data:
        if text == "💳 Реквизиты":
            await show_payment_info(message)
        elif text == "📞 Поддержка":
            await show_support(message)
        else:
            await message.answer("ℹ️ Используйте кнопки меню для навигации", reply_markup=main_menu())
        return
    
    data = user_data[user_id]
    step = data.get("step")
    
    # Описание
    if step == "description":
        if len(text) < 10:
            await message.answer("❌ Описание слишком короткое. Напишите минимум 10 символов.",
                               parse_mode="HTML")
            return
        data["description"] = text
        data["step"] = "price"
        save_user_data()
        await message.answer(
            "<b>💰 Шаг 3: Цена</b>\n\n"
            "Укажите цену в сомах:\n\n"
            "<i>Примеры:</i>\n"
            "• 1500\n"
            "• 1000-1500 (диапазон)\n"
            "• Договорная\n"
            "• От 1000 сом\n\n"
            "<b>Ваша цена:</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔙 Назад")]],
                resize_keyboard=True
            )
        )
    
    # Цена
    elif step == "price":
        data["price"] = text
        data["step"] = "contact_type"
        save_user_data()
        
        await message.answer(
            "<b>📞 Шаг 4: Контакты</b>\n\n"
            "Выберите, как с вами связаться:\n\n"
            "<b>📱 Телефон</b> - укажите номер телефона\n"
            "<b>📞 Telegram (авто)</b> - автоматически использует ваш username\n\n"
            "<b>Выберите вариант:</b>",
            parse_mode="HTML",
            reply_markup=contact_type_menu()
        )
    
    # Тип контактов
    elif step == "contact_type":
        if text == "📱 Телефон":
            data["contact_type"] = "phone"
            data["step"] = "contact_value"
            save_user_data()
            await message.answer(
                "<b>📱 Введите номер телефона:</b>\n\n"
                "<i>Формат:</i> +996 XXX XXX XXX\n"
                "<i>Пример:</i> +996 555 123456\n\n"
                "<b>Укажите ваш номер:</b>",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="🔙 Назад")]],
                    resize_keyboard=True
                )
            )
        elif text == "📞 Telegram (авто)":
            username = message.from_user.username
            if username:
                data["contact_type"] = "telegram"
                data["contacts"] = f"@{username}"
                data["step"] = "location_choice"
                save_user_data()
                
                await message.answer(
                    "<b>✅ Контакты сохранены!</b>\n\n"
                    f"<b>Ваш Telegram:</b> @{username}\n\n"
                    "Переходим к следующему шагу:",
                    parse_mode="HTML"
                )
                
                await message.answer(
                    "<b>📍 Шаг 5: Локация</b>\n\n"
                    "Укажите, где находятся цветы:\n\n"
                    "<b>📍 Отправить геолокацию</b> - отправить точное местоположение\n"
                    "<b>🏙️ Ввести город/район</b> - указать район или город\n"
                    "<b>🚫 Без локации</b> - не указывать адрес\n\n"
                    "<b>Выберите вариант:</b>",
                    parse_mode="HTML",
                    reply_markup=location_menu()
                )
            else:
                await message.answer(
                    "❌ <b>У вас нет username в Telegram</b>\n\n"
                    "Пожалуйста:\n"
                    "1. Установите username в настройках Telegram\n"
                    "2. Или выберите вариант 'Телефон'\n\n"
                    "Как получить username:\n"
                    "Настройки → Имя пользователя → Установить username",
                    parse_mode="HTML",
                    reply_markup=contact_type_menu()
                )
        elif text == "🔙 Назад":
            await back_command(message)
    
    # Значение контактов (телефон)
    elif step == "contact_value":
        contact_type = data.get("contact_type")
        
        if contact_type == "phone":
            # Проверяем номер телефона
            phone = clean_phone_number(text)
            if not is_valid_phone(phone):
                await message.answer("❌ Неверный формат номера. Используйте:\n+996 XXX XXX XXX",
                                   parse_mode="HTML")
                return
            data["contacts"] = phone
            data["step"] = "location_choice"
            save_user_data()
            
            await message.answer(
                "<b>✅ Контакты сохранены!</b>\n\n"
                f"<b>Ваш телефон:</b> {phone}\n\n"
                "Переходим к следующему шагу:",
                parse_mode="HTML"
            )
            
            await message.answer(
                "<b>📍 Шаг 5: Локация</b>\n\n"
                "Укажите, где находятся цветы:\n\n"
                "<b>📍 Отправить геолокацию</b> - отправить точное местоположение\n"
                "<b>🏙️ Ввести город/район</b> - указать район или город\n"
                "<b>🚫 Без локации</b> - не указывать адрес\n\n"
                "<b>Выберите вариант:</b>",
                parse_mode="HTML",
                reply_markup=location_menu()
            )
    
    # Выбор способа указания локации
    elif step == "location_choice":
        if text == "📍 Отправить геолокацию":
            data["step"] = "location_value"
            save_user_data()
            await message.answer(
                "<b>📍 Отправьте ваше местоположение</b>\n\n"
                "Нажмите на кнопку ниже, чтобы отправить геолокацию.\n\n"
                "<i>Совет:</i> Включите GPS для большей точности",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)],
                        [KeyboardButton(text="🔙 Назад")]
                    ],
                    resize_keyboard=True
                )
            )
        elif text == "🏙️ Ввести город/район":
            data["step"] = "location_value"
            save_user_data()
            await message.answer(
                "<b>🏙️ Введите город или район:</b>\n\n"
                "<i>Примеры:</i>\n"
                "• г. Бишкек, центр\n"
                "• г. Ош, район Алай\n"
                "• мкр. Аламедин-1\n"
                "• с. Беш-Кунгей\n\n"
                "<b>Ваш адрес:</b>",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="🔙 Назад")]],
                    resize_keyboard=True
                )
            )
        elif text == "🚫 Без локации":
            data["step"] = "preview"
            data["location"] = {"type": "none", "address": "Не указано"}
            save_user_data()
            await show_preview(message, data)
        elif text == "🔙 Назад":
            await back_command(message)
    
    # Ввод локации вручную
    elif step == "location_value":
        if text == "🔙 Назад":
            await back_command(message)
        else:
            # Сохраняем адрес
            data["location"] = {
                "type": "address",
                "address": text
            }
            data["step"] = "preview"
            save_user_data()
            
            await message.answer(f"✅ <b>Адрес сохранен!</b>\n\n"
                               f"<b>Локация:</b> {text}",
                               parse_mode="HTML")
            
            await show_preview(message, data)
    
    # Превью и подтверждение
    elif step == "preview":
        if text.lower() == "✅ опубликовать":
            data["step"] = "waiting_payment"
            save_user_data()
            
            await message.answer(
                f"💵 <b>Оплатите {PRICE} сом</b>\n\n"
                f"<b>Реквизиты:</b>\n"
                f"O!Money: <code>+996 707 770 740</code>\n"
                f"MegaPay: <code>+996 707 770 740</code>\n\n"
                f"📎 <b>После оплаты отправьте скриншот чека.</b>\n"
                f"⏱ Обычно проверка занимает 10-30 минут.\n\n"
                f"<b>Ваше объявление сохранено и ожидает оплаты.</b>",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="💳 Реквизиты")],
                        [KeyboardButton(text="📱 Классический режим")]
                    ],
                    resize_keyboard=True
                )
            )
        elif text.lower() == "✏️ редактировать":
            # Возвращаем к началу
            data["step"] = "waiting_photos"
            data["photos"] = []
            save_user_data()
            await message.answer(
                "<b>🔄 Начинаем заново</b>\n\n"
                "Отправьте фото цветов для нового объявления:",
                parse_mode="HTML"
            )
        elif text == "🔙 Назад":
            await back_command(message)
    
    # Ожидание оплаты (только для классического режима)
    elif step == "waiting_payment":
        if "photos" in data and data["photos"]:
            await message.answer("📎 Отправьте скриншот оплаты (фото)")
        else:
            await message.answer("❌ Отправьте скриншот оплаты в виде фото")

async def show_preview(message: Message, data: Dict):
    """Показывает превью объявления"""
    
    # Экранируем данные для HTML
    description = escape_html(data.get('description', 'Не указано'))
    price = escape_html(data.get('price', 'Не указана'))
    contacts = escape_html(data.get('contacts', 'Не указаны'))
    
    # Форматируем контакты
    if data.get('contact_type') == 'telegram':
        username = data.get('contacts', '').lstrip('@')
        contacts_display = f'📞 Telegram: @{username}'
    else:
        contacts_display = f'📱 Телефон: {contacts}'
    
    # Форматируем фото
    photos_count = len(data.get('photos', []))
    photos_display = f"📸 Фото: {photos_count} шт."
    
    # Форматируем локацию
    location_info = data.get('location', {"type": "none", "address": "Не указано"})
    location_display = ""
    
    if location_info["type"] == "coordinates":
        lat = location_info["latitude"]
        lon = location_info["longitude"]
        address = escape_html(location_info.get('address', ''))
        map_url = f"https://maps.google.com/?q={lat},{lon}"
        if address:
            location_display = f'📍 Локация: <a href="{map_url}">{address}</a>'
        else:
            location_display = f'📍 Локация: <a href="{map_url}">{lat}, {lon}</a>'
    elif location_info["type"] == "address":
        address = escape_html(location_info["address"])
        encoded_address = address.replace(' ', '+')
        map_url = f"https://maps.google.com/?q={encoded_address}"
        location_display = f'📍 Локация: <a href="{map_url}">{address}</a>'
    else:
        location_display = "📍 Локация: Не указана"
    
    preview = f"""
<b>📋 ПРЕВЬЮ ОБЪЯВЛЕНИЯ</b>

{photos_display}
📝 <b>Описание:</b> {description}
💰 <b>Цена:</b> {price}
{contacts_display}
{location_display}

💵 <b>Стоимость публикации:</b> {PRICE} сом

<b>Всё верно?</b>
"""
    
    await message.answer(preview, parse_mode="HTML", reply_markup=preview_menu())

async def process_payment_screenshot(message: Message, screenshot_id: str):
    """Обработка скриншота оплаты"""
    user_id = message.from_user.id
    username = message.from_user.username or "нет"
    
    logger.info(f"СКРИНШОТ от {user_id} (@{username})")
    
    if user_id not in user_data:
        await message.answer("❌ Сначала создайте объявление!")
        return
    
    data = user_data[user_id]
    
    # Экранируем данные для HTML
    description = escape_html(data.get('description', 'Не указано'))
    price = escape_html(data.get('price', 'Не указана'))
    contacts = escape_html(data.get('contacts', 'Не указаны'))
    
    # Форматируем контакты
    if data.get('contact_type') == 'telegram':
        username_contact = data.get('contacts', '').lstrip('@')
        contacts_display = f'📞 Telegram: @{username_contact}'
    else:
        contacts_display = f'📱 Телефон: {contacts}'
    
    # Форматируем фото
    photos_count = len(data.get('photos', []))
    photos_display = f"📸 Фото: {photos_count} шт."
    
    # Форматируем локацию
    location_info = data.get('location', {"type": "none", "address": "Не указано"})
    location_display = ""
    
    if location_info["type"] == "coordinates":
        lat = location_info["latitude"]
        lon = location_info["longitude"]
        address = escape_html(location_info.get('address', ''))
        if address:
            location_display = f'📍 <b>Локация:</b> {address} ({lat}, {lon})'
        else:
            location_display = f'📍 <b>Локация:</b> {lat}, {lon}'
    elif location_info["type"] == "address":
        address = escape_html(location_info["address"])
        location_display = f'📍 <b>Локация:</b> {address}'
    else:
        location_display = "📍 <b>Локация:</b> Не указана"
    
    # Формируем текст для админа
    admin_text = f"""
<b>🌸 НОВАЯ ЗАЯВКА!</b>

👤 <b>Пользователь:</b> @{username}
📱 <b>ID:</b> {user_id}
⏰ <b>Время:</b> {datetime.now().strftime('%H:%M %d.%m.%Y')}

{photos_display}
📝 <b>Описание:</b> {description}
💰 <b>Цена:</b> {price}
{contacts_display}
{location_display}

💵 <b>Сумма:</b> {PRICE} сом
"""
    
    # Отправляем админу
    try:
        # Отправляем первое фото из объявления (если есть)
        if data.get("photos"):
            first_photo = data["photos"][0]
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=first_photo,
                caption=admin_text[:1024],
                parse_mode="HTML",
                reply_markup=get_admin_keyboard(user_id)
            )
            # Отправляем скриншот оплаты отдельно
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=screenshot_id,
                caption="📸 <b>Скриншот оплаты</b>"
            )
        else:
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=screenshot_id,
                caption=admin_text[:1024],
                parse_mode="HTML",
                reply_markup=get_admin_keyboard(user_id)
            )
    except Exception as e:
        logger.error(f"Ошибка отправки админу: {e}")
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"{admin_text}\n\n⚠️ <b>Скриншот оплаты:</b> {screenshot_id[:50]}...",
            parse_mode="HTML",
            reply_markup=get_admin_keyboard(user_id)
        )
    
    # Уведомляем пользователя
    await message.answer(
        "✅ <b>Скриншот получен!</b>\n\n"
        "Ваш скриншот отправлен администратору.\n"
        "Обычно проверка занимает 10-30 минут.\n\n"
        "После подтверждения объявление будет опубликовано.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )

# ==================== АДМИН ====================

@dp.callback_query(F.data.startswith("publish_"))
async def publish_callback(callback: CallbackQuery):
    """Админ публикует объявление"""
    user_id = int(callback.data.split("_")[1])
    
    try:
        if user_id not in user_data:
            await callback.message.answer(f"❌ Данные пользователя {user_id} не найдены!")
            await callback.answer()
            return
        
        data = user_data[user_id]
        
        if not data.get("photos"):
            await callback.message.answer(f"❌ У пользователя {user_id} нет фото!")
            await callback.answer()
            return
        
        photos = data.get("photos", [])
        description = escape_html(data.get("description", "Не указано"))
        price = escape_html(data.get("price", "Не указана"))
        contacts = escape_html(data.get("contacts", "Не указаны"))
        
        # Форматируем контакты
        if data.get('contact_type') == 'telegram':
            username = data.get('contacts', '').lstrip('@')
            contacts_display = f'📞 Telegram: @{username}'
        else:
            contacts_display = f'📱 Телефон: {contacts}'
        
        # Форматируем локацию
        location_info = data.get('location', {"type": "none", "address": "Не указано"})
        location_display = ""
        
        if location_info["type"] == "coordinates":
            lat = location_info["latitude"]
            lon = location_info["longitude"]
            address = escape_html(location_info.get('address', ''))
            map_url = f"https://maps.google.com/?q={lat},{lon}"
            if address:
                location_display = f'\n📍 <b>Локация:</b> <a href="{map_url}">{address}</a>'
            else:
                location_display = f'\n📍 <b>Локация:</b> <a href="{map_url}">{lat}, {lon}</a>'
        elif location_info["type"] == "address":
            address = escape_html(location_info["address"])
            encoded_address = address.replace(' ', '+')
            map_url = f"https://maps.google.com/?q={encoded_address}"
            location_display = f'\n📍 <b>Локация:</b> <a href="{map_url}">{address}</a>'
        
        # Формируем пост
        post_text = f"""
<b>🌸 ДОСТУПНО ПРЯМО СЕЙЧАС!</b>

{description}

💰 <b>Цена:</b> {price}
{contacts_display}{location_display}

#цветы #продажа #кыргызстан #цветыкг
"""
        
        # Публикуем в канале с фото
        if photos:
            # Отправляем первый фото с подписью
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photos[0],
                caption=post_text,
                parse_mode="HTML"
            )
            
            # Отправляем остальные фото
            for photo in photos[1:]:
                await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=photo
                )
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                chat_id=user_id,
                text="✅ <b>Ваше объявление опубликовано в канале!</b>\n\n"
                     "Спасибо за использование нашего сервиса! 🌸\n\n"
                     "Для создания нового объявления нажмите /start",
                parse_mode="HTML",
                reply_markup=main_menu()
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя: {e}")
        
        # Удаляем данные
        if user_id in user_data:
            del user_data[user_id]
            save_user_data()
        
        # Удаляем сообщение с кнопками
        await callback.message.delete()
        await callback.answer("✅ Объявление опубликовано!")
        
    except Exception as e:
        logger.error(f"Ошибка публикации: {e}")
        await callback.message.answer(f"❌ Ошибка: {e}")
        await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def reject_callback(callback: CallbackQuery):
    """Админ отклоняет объявление"""
    user_id = int(callback.data.split("_")[1])
    
    if user_id in user_data:
        del user_data[user_id]
        save_user_data()
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ <b>Ваше объявление отклонено администратором.</b>\n\n"
                 "Возможные причины:\n"
                 "• Нечеткие фото\n"
                 "• Неполная информация\n"
                 "• Нарушение правил\n\n"
                 "Если это ошибка, свяжитесь с поддержкой: @admin",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя: {e}")
    
    await callback.message.delete()
    await callback.answer("❌ Объявление отклонено")

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def escape_html(text):
    """Экранирует HTML символы"""
    if text is None:
        return ""
    return html.escape(str(text))

def clean_phone_number(phone):
    """Очищает номер телефона"""
    # Удаляем все нецифровые символы кроме +
    phone = re.sub(r'[^\d+]', '', phone)
    
    # Если номер начинается с 996, добавляем +
    if phone.startswith('996') and not phone.startswith('+996'):
        phone = '+' + phone
    
    # Если номер без кода страны, добавляем код Кыргызстана
    if len(phone) == 9 and phone.isdigit():
        phone = '+996' + phone
    
    return phone

def is_valid_phone(phone):
    """Проверяет валидность номера телефона"""
    # Проверяем формат +996XXXXXXXXX
    pattern = r'^\+996\d{9}$'
    return bool(re.match(pattern, phone))

# ==================== WEB APP ОБРАБОТКА ====================

@dp.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    """Обработка данных из Web App"""
    try:
        user_id = message.from_user.id
        web_app_data = json.loads(message.web_app_data.data)
        
        logger.info(f"WebApp данные от {user_id}: {web_app_data}")
        
        # Получаем username пользователя
        username = message.from_user.username or "нет username"
        
        # Сохраняем данные из Web App
        user_data[user_id] = {
            "step": "waiting_payment",
            "mode": "web_app",
            "photos": [],  # Фото должны быть отправлены отдельно через чат
            "description": web_app_data.get("description", ""),
            "price": web_app_data.get("price", ""),
            "contact_type": web_app_data.get("contact_type", "telegram"),
            "contacts": web_app_data.get("contacts", f"@{username}" if username != "нет username" else ""),
            "location": web_app_data.get("location", ""),
            "username": username,
            "timestamp": web_app_data.get("timestamp", datetime.now().isoformat())
        }
        save_user_data()
        
        # Отправляем инструкцию по оплате
        payment_text = f"""
<b>✅ Данные из формы получены!</b>

📝 <b>Описание:</b> {escape_html(user_data[user_id]['description'])}
💰 <b>Цена:</b> {escape_html(user_data[user_id]['price'])}
📞 <b>Контакты:</b> {escape_html(user_data[user_id]['contacts'])}
📍 <b>Локация:</b> {escape_html(user_data[user_id]['location'])}

💵 <b>Стоимость публикации:</b> {PRICE} сом

<b>Теперь выполните следующие шаги:</b>

1. <b>Отправьте фото товара</b> в этот чат (можно несколько, до 10 фото)
2. <b>Оплатите {PRICE} сом</b> по реквизитам
3. <b>Отправьте скриншот оплаты</b> в этот чат

<b>Реквизиты:</b>
O!Money: <code>+996 707 770 740</code>
MegaPay: <code>+996 707 770 740</code>

После проверки ваше объявление будет опубликовано в канале.
"""
        
        await message.answer(payment_text, parse_mode="HTML")
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        await message.answer("❌ Ошибка обработки данных. Попробуйте еще раз.", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Ошибка обработки WebApp данных: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.", reply_markup=main_menu())

# ==================== ЗАПУСК ====================

async def main():
    """Основная функция запуска бота"""
    print("=" * 60)
    print("🤖 FLOWER MARKET BOT (WEB APP + КЛАССИЧЕСКИЙ РЕЖИМ)")
    print("=" * 60)
    print(f"🔑 Админ: {ADMIN_ID}")
    print(f"📢 Канал: {CHANNEL_ID}")
    print(f"💰 Цена: {PRICE} сом")
    print(f"🌐 Web App URL: {WEB_APP_URL}")
    print(f"💾 Загружено заявок: {len(user_data)}")
    print("=" * 60)
    print("✨ Основные функции:")
    print("• 🌐 Web App форма для удобного создания")
    print("• 📱 Классический режим через чат")
    print("• 📸 Загрузка нескольких фото (до 10)")
    print("• 📍 Локация на карте с определением адреса")
    print("• 🤖 Автоматическое определение Telegram username")
    print("• 💳 Оплата и модерация")
    print("=" * 60)
    print("✅ Бот запущен! Напишите /start")
    print("=" * 60)
    
    try:
        await dp.start_polling(bot)
    finally:
        # Сохраняем данные при завершении
        save_user_data()

if __name__ == "__main__":
    if sys.platform == 'darwin':
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
        save_user_data()