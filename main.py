```python
import os
import logging
from datetime import datetime
from io import BytesIO
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from draw_map import draw_map

# === Настройка логирования ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Константы состояний ===
(
    LANG, ASK_NAME, MENU,
    BOOK_DATE, BOOK_TIME, BOOK_COUNT, BOOK_ZONE, BOOK_CONFIRM, BOOK_PREPAY,
    AI_ALLERGY, AI_MENU,
    MUSIC_TITLE, MUSIC_CONFIRM,
    FEEDBACK_CHOICE, FEEDBACK_TEXT,
) = range(15)

# === Загрузка переменных окружения ===
BOT_TOKEN = os.getenv('BOT_TOKEN')
GROUP_CHAT_ID = int(os.getenv('GROUP_CHAT_ID', '0'))

# === Хендлеры ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Команда /start: выбор языка"""
    keyboard = [["🇷🇺 Русский", "🇬🇧 English"]]
    reply = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите язык / Choose language:", reply_markup=reply)
    return LANG

async def lang_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняем язык и спрашиваем имя"""
    text = update.message.text
    context.user_data['lang'] = 'ru' if 'рус' in text.lower() else 'en'
    prompt = 'Как я могу к вам обращаться?' if context.user_data['lang']=='ru' else 'How may I call you?'
    await update.message.reply_text(prompt, reply_markup=ReplyKeyboardMarkup([], remove_keyboard=True))
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняем имя и показываем главное меню"""
    name = update.message.text.strip()
    context.user_data['name'] = name
    lang = context.user_data['lang']
    greeting = f"Привет, {name}! Выберите раздел:" if lang=='ru' else f"Hello, {name}! Choose section:"
    kb = [
        [KeyboardButton("📅 Просмотреть меню"), KeyboardButton("🪑 Забронировать столик")],
        [KeyboardButton("🤖 AI-меню"), KeyboardButton("🎵 Заказать музыку")],
        [KeyboardButton("✍️ Оставить отзыв")],
    ]
    await update.message.reply_text(greeting, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return MENU

# --- Главное меню маршрутизация ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    lang = context.user_data.get('lang', 'ru')
    if 'заброни' in text.lower() or '🪑' in text:
        # Начнем бронирование
        prompt = 'Введите дату брони (YYYY-MM-DD):' if lang=='ru' else 'Enter booking date (YYYY-MM-DD):'
        await update.message.reply_text(prompt)
        return BOOK_DATE
    if 'ai' in text.lower() or '🤖' in text:
        prompt = 'Укажите аллергии (через запятую) или "нет":' if lang=='ru' else 'List allergies comma-separated or "no":'
        await update.message.reply_text(prompt)
        return AI_ALLERGY
    if 'музык' in text.lower() or '🎵' in text:
        prompt = 'Введите название трека:' if lang=='ru' else 'Enter track title:'
        await update.message.reply_text(prompt)
        return MUSIC_TITLE
    if 'отзыв' in text.lower() or '✍️' in text:
        kb = [["Анонимно", "С именем"]]
        await update.message.reply_text('Как вы хотите отправить отзыв?' if lang=='ru' else 'Send feedback anonymously or with name?', reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))
        return FEEDBACK_CHOICE
    if 'меню' in text.lower() or '📅' in text:
        # Пример меню
        menu = '- Салат\n- Стейк\n- Десерт'
        await update.message.reply_text('Наше меню:\n' + menu if lang=='ru' else 'Our menu:\n' + menu)
        return MENU
    await update.message.reply_text('Не распознал команду, выберите раздел.')
    return MENU

# --- Бронирование ---
async def book_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['date'] = update.message.text.strip()
    lang = context.user_data['lang']
    prompt = 'Введите время (HH:MM):' if lang=='ru' else 'Enter time (HH:MM):'
    await update.message.reply_text(prompt)
    return BOOK_TIME

async def book_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['time'] = update.message.text.strip()
    lang = context.user_data['lang']
    prompt = 'Сколько гостей?' if lang=='ru' else 'Number of guests?'
    await update.message.reply_text(prompt)
    return BOOK_COUNT

async def book_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['count'] = update.message.text.strip()
    # Генерируем схему зала
    img = draw_map(booked_seats=[])
    await update.message.reply_photo(photo=img, caption='Схема зала: 🟢 свободно, 🔴 занято')
    lang = context.user_data['lang']
    prompt = 'Выберите зону (VIP, Балкон, Танцпол, Бар):' if lang=='ru' else 'Choose zone (VIP, Balcony, Dancefloor, Bar):'
    await update.message.reply_text(prompt)
    return BOOK_ZONE

async def book_zone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['zone'] = update.message.text.strip()
    d = context.user_data
    lang = d['lang']
    summary = f"Дата: {d['date']}\nВремя: {d['time']}\nГостей: {d['count']}\nЗона: {d['zone']}"
    prompt = ('Подтвердить и оплатить предоплату 1000 сом? (да/нет)' if lang=='ru' else 'Confirm and prepay 1000 som? (yes/no)')
    await update.message.reply_text(summary + '\n' + prompt)
    return BOOK_CONFIRM

async def book_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ans = update.message.text.strip().lower()
    lang = context.user_data['lang']
    if ans in ('да','yes'):
        # Генерация QR-кода-заглушка
        qr = BytesIO()
        im = Image.new('RGB',(200,200),'white')
        d = ImageDraw.Draw(im)
        d.text((50,90),'QR HERE',fill='black')
        im.save(qr,'PNG'); qr.seek(0)
        await update.message.reply_photo(photo=qr, caption='Сканируйте для оплаты')
        # Уведомление в группу
        d = context.user_data
        msg = f"Новая бронь от {d['name']}: {d['date']} {d['time']}, {d['count']} guests, zone {d['zone']}"
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg)
        await update.message.reply_text('Бронь подтверждена!' if lang=='ru' else 'Booking confirmed!')
    else:
        await update.message.reply_text('Отменено.' if lang=='ru' else 'Cancelled.')
    return MENU

# --- AI-меню ---
async def ai_allergy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['allergy'] = update.message.text.strip().lower()
    lang = context.user_data['lang']
    await update.message.reply_text('Формирую меню…' if lang=='ru' else 'Building menu…')
    # Пример фильтрации
    menu = ['Салат (зелень)','Пицца (сыр)','Стейк (мясо)']
    filtered = [m for m in menu if context.user_data['allergy'] not in m.lower()]
    out = '\n'.join(filtered) or ('Нет позиций' if lang=='ru' else 'No items')
    await update.message.reply_text(out)
    return MENU

# --- Заказ музыки ---
async def music_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['track'] = update.message.text.strip()
    await update.message.reply_text('Оплата 500 сом… (заглушка)')
    # После оплаты сразу уведомляем
    d = context.user_data; lang = d['lang']
    dj = 'DJ Nox'
    msg = f"Заказ музыки: {d['track']} | DJ: {dj} | @{d['name']}"
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg)
    await update.message.reply_text('Трек заказан!' if lang=='ru' else 'Track ordered!')
    return MENU

# --- Отзыв ---
async def feedback_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['anon'] = (update.message.text=='Анонимно')
    await update.message.reply_text('Введите текст отзыва:')
    return FEEDBACK_TEXT

async def feedback_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    author = 'Аноним' if context.user_data['anon'] else context.user_data['name']
    msg = f"Отзыв от {author}: {text}"
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg)
    await update.message.reply_text('Спасибо за отзыв!')
    return MENU

# --- Строим application и запускаем ---
def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    # сброс webhooks и очистка
    app.bot.delete_webhook(drop_pending_updates=True)

    # хендлеры
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.Regex('🇷🇺|🇬🇧'), lang_chosen))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler), group=2)

    # бронирование разговор
    book_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('🪑'), menu_handler)],
        states={
            BOOK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_date)],
            BOOK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_time)],
            BOOK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_count)],
            BOOK_ZONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_zone)],
            BOOK_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_confirm)],
        },
        fallbacks=[]
    )
    app.add_handler(book_conv)

    # AI
    app.add_handler(MessageHandler(filters.Regex('🤖'), ai_allergy))

    # музыка
    app.add_handler(MessageHandler(filters.Regex('🎵'), music_title))

    # отзыв
    fb_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('✍️'), menu_handler)],
        states={FEEDBACK_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_choice)],
                FEEDBACK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_text)]},
        fallbacks=[]
    )
    app.add_handler(fb_conv)

    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
```

---
