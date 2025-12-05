import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
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

# === КОНФИГУРАЦИЯ ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8299558870:AAEAVbDQIgFi2F3sjcfy8g2Win5McImcGaQ")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6174995259))
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1003393988300")
PRICE = int(os.getenv("PRICE_PER_POST", 50))

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# FSM состояния
class Form(StatesGroup):
    waiting_photos = State()
    description = State()
    price = State()
    contact_type = State()
    phone = State()
    location = State()
    waiting_payment = State()

# Хранилище данных
STORAGE_FILE = "user_requests.json"

def load_data() -> Dict:
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data: Dict):
    with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_data = load_data()

# Клавиатуры
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌸 Создать объявление", web_app=WebAppInfo(url="https://ваш-сайт.vercel.app"))],
            [KeyboardButton(text="💳 Реквизиты"), KeyboardButton(text="📞 Поддержка")],
            [KeyboardButton(text="📱 Классический режим")]
        ],
        resize_keyboard=True
    )

def get_admin_keyboard(user_id: int, ad_id: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve_{user_id}_{ad_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}_{ad_id}")
            ]
        ]
    )

# Команды
@dp.message(Command("start"))
async def cmd_start(message: Message):
    welcome = f"""
<b>🌸 Flower Market Bot</b>

💰 <b>Стоимость публикации:</b> {PRICE} сом

✨ <b>Создайте красивое объявление:</b>

<b>1. 🌐 Веб-приложение (рекомендуется)</b>
• Удобная форма с предпросмотром
• Автозаполнение данных
• Загрузка нескольких фото

<b>2. 📱 Классический режим</b>
• Пошаговое создание в чате
• Поддержка геолокации

💳 <b>Реквизиты:</b>
• O!Money: <code>+996 707 770 740</code>
• MegaPay: <code>+996 707 770 740</code>
"""
    await message.answer(welcome, parse_mode="HTML", reply_markup=main_menu())

# Обработка Web App данных
@dp.message(types.WebAppData)
async def web_app_data(message: types.WebAppData):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        
        # Сохраняем данные из Web App
        import uuid
        ad_id = str(uuid.uuid4())[:8]
        
        user_data[ad_id] = {
            "user_id": user_id,
            "username": message.from_user.username,
            **data,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        save_data(user_data)
        
        # Отправляем админу
        admin_text = f"""
🆕 <b>НОВОЕ ОБЪЯВЛЕНИЕ из Web App</b>

ID: #{ad_id}
Пользователь: @{message.from_user.username or 'нет'}
Цена: {data.get('price', 'Не указана')}
Локация: {data.get('location', {}).get('address', 'Не указана')}
Описание: {data.get('description', '')[:200]}...
"""
        
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=get_admin_keyboard(user_id, ad_id)
        )
        
        # Инструкция пользователю
        await message.answer(
            f"✅ <b>Объявление #{ad_id} создано!</b>\n\n"
            f"💳 <b>Оплатите {PRICE} сом:</b>\n"
            f"O!Money: <code>+996 707 770 740</code>\n"
            f"MegaPay: <code>+996 707 770 740</code>\n\n"
            f"📎 <b>Отправьте скриншот оплаты с пометкой #{ad_id}</b>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"WebApp error: {e}")
        await message.answer("❌ Ошибка обработки данных")

# Обработка callback'ов
@dp.callback_query(lambda c: c.data.startswith('approve_') or c.data.startswith('reject_'))
async def process_callback(callback: CallbackQuery):
    try:
        _, action, user_id, ad_id = callback.data.split('_')
        ad = user_data.get(ad_id)
        
        if not ad:
            await callback.answer("Объявление не найдено")
            return
        
        if action == 'approve':
            # Публикация в канал
            post_text = f"""
🌸 <b>{ad.get('description', '')[:100]}...</b>

💰 Цена: {ad.get('price', 'Не указана')}
📞 Контакты: {ad.get('contacts', 'Не указаны')}
📍 Локация: {ad.get('location', {}).get('address', 'Не указана')}

#цветы #продажа #кыргызстан
"""
            await bot.send_message(CHANNEL_ID, post_text, parse_mode="HTML")
            
            # Уведомление пользователя
            await bot.send_message(
                int(user_id),
                f"✅ <b>Ваше объявление #{ad_id} опубликовано!</b>\n\n"
                f"Спасибо за использование нашего сервиса! 🌸",
                parse_mode="HTML"
            )
            
            await callback.message.edit_text(f"✅ Объявление #{ad_id} опубликовано")
            
        elif action == 'reject':
            await bot.send_message(
                int(user_id),
                f"❌ <b>Объявление #{ad_id} отклонено</b>\n\n"
                f"Если это ошибка, свяжитесь с поддержкой.",
                parse_mode="HTML"
            )
            await callback.message.edit_text(f"❌ Объявление #{ad_id} отклонено")
        
        # Удаляем из хранилища
        if ad_id in user_data:
            del user_data[ad_id]
            save_data(user_data)
            
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await callback.answer("Ошибка обработки")

# Запуск бота
async def main():
    logger.info("Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())