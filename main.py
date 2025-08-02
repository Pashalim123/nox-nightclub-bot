import os
import logging
import requests
from datetime import datetime

from PIL import Image, ImageDraw               # Pillow вместо PIL
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# === Настройка логирования ===
logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# === Константы и чтение из .env ===
TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))

# Перед запуском polling удаляем любой webhook, чтобы не было конфликта
if TOKEN:
    requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true")

# === Состояния для ConversationHandler ===
(
    LANG, NAME, MENU,
    BOOK_DATE, BOOK_TIME, BOOK_GUESTS, BOOK_ZONE, BOOK_CONFIRM,
    AI_ALLERGY,
    MUSIC_TITLE, MUSIC_CONFIRM,
    REVIEW_TEXT, REVIEW_ANON,
) = range(13)

# === Хелперы для отрисовки схемы зала ===
def draw_map():
    """
    Создаём простую карту зала 400×300 с подписями зон.
    🔴 / 🟢 будем рисовать потом поверх, когда придёт статус.
    """
    img = Image.new("RGB", (400, 300), "white")
    d = ImageDraw.Draw(img)
    # Рисуем 4 зоны примитивно
    d.rectangle([( 20,  20), (180, 140)], outline="black")
    d.text(( 30,  30), "VIP", fill="black")
    d.rectangle([(220,  20), (380, 140)], outline="black")
    d.text((230,  30), "BAR", fill="black")
    d.rectangle([( 20, 160), (180, 280)], outline="black")
    d.text(( 30, 170), "Балкон", fill="black")
    d.rectangle([(220, 160), (380, 280)], outline="black")
    d.text((230, 170), "Танцпол", fill="black")
    return img

# === Обработчики ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["Русский", "English"]]
    await update.message.reply_text(
        "Выберите язык / Choose language:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return LANG

async def lang_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    txt = update.message.text
    context.user_data["lang"] = "ru" if "Рус" in txt else "en"
    prompt = "Как я могу к вам обращаться?" if context.user_data["lang"]=="ru" else "How can I call you?"
    await update.message.reply_text(prompt, reply_markup=ReplyKeyboardMarkup([], remove_keyboard=True))
    return NAME

async def name_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.message.text
    name = context.user_data["name"]
    lang = context.user_data["lang"]
    greet = f"Привет, {name}! Добро пожаловать в NOX." if lang=="ru" else f"Hello, {name}! Welcome to NOX."
    menu = [
        ["🪑 Забронировать столик", "📅 AI-меню"],
        ["🎵 Заказать музыку", "✍️ Оставить отзыв"],
    ]
    await update.message.reply_text(
        greet,
        reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True)
    )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    lang = context.user_data["lang"]
    if text.startswith("🪑"):
        await update.message.reply_text("Введите дату бронирования (YYYY-MM-DD):")
        return BOOK_DATE
    if text.startswith("📅"):
        await update.message.reply_text(
            "Укажите аллергии, ингредиенты через запятую:",
        )
        return AI_ALLERGY
    if text.startswith("🎵"):
        await update.message.reply_text("Введите название трека для заказа:")
        return MUSIC_TITLE
    if text.startswith("✍️"):
        await update.message.reply_text("Введите ваш отзыв:")
        return REVIEW_TEXT
    # на всякий случай
    await update.message.reply_text("Пожалуйста, выберите пункт меню.")
    return MENU

# — Бронирование —
async def book_date(update, context) -> int:
    context.user_data["book_date"] = update.message.text
    await update.message.reply_text("Введите время (HH:MM):")
    return BOOK_TIME

async def book_time(update, context) -> int:
    context.user_data["book_time"] = update.message.text
    await update.message.reply_text("Сколько человек?")
    return BOOK_GUESTS

async def book_guests(update, context) -> int:
    context.user_data["book_guests"] = update.message.text
    # присылаем карту зала
    img = draw_map()
    with open("hall_map.png","wb") as f:
        img.save(f, format="PNG")
    await update.message.reply_photo(photo=open("hall_map.png","rb"), caption="Выберите зону: VIP, BAR, Балкон, Танцпол")
    return BOOK_ZONE

async def book_zone(update, context) -> int:
    context.user_data["book_zone"] = update.message.text
    d = context.user_data
    info = (
        f"Дата: {d['book_date']}\n"
        f"Время: {d['book_time']}\n"
        f"Гостей: {d['book_guests']}\n"
        f"Зона: {d['book_zone']}\n"
        "Подтвердить бронь и оплатить 1000 сом?"
    )
    kb = [["Подтвердить","Отмена"]]
    await update.message.reply_text(info, reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
    return BOOK_CONFIRM

async def book_confirm(update, context) -> int:
    if update.message.text == "Подтвердить":
        await update.message.reply_text("Спасибо, ваша бронь подтверждена! Ссылка для оплаты: <QR-CODE-LINK>")
        # уведомляем группу
        d = context.user_data
        msg = (
            f"📌 *Новая бронь*\n"
            f"👤 {d['name']}\n"
            f"📅 {d['book_date']} {d['book_time']}\n"
            f"👥 {d['book_guests']} чел.\n"
            f"🏷 {d['book_zone']}\n"
        )
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg, parse_mode="Markdown")
    else:
        await update.message.reply_text("Отменено.")
    return MENU

# — AI-меню —
async def ai_allergy(update, context) -> int:
    alle = [x.strip().lower() for x in update.message.text.split(",")]
    context.user_data["allergies"] = alle
    # здесь можно подгрузить реальное меню из БД
    full_menu = ["Салат Цезарь", "Пицца 4 сыра", "Бургер с говядиной"]
    ok = [item for item in full_menu if not any(a in item.lower() for a in alle)]
    await update.message.reply_text("Доступные блюда:\n" + "\n".join(ok))
    return MENU

# — Музыка —
async def music_title(update, context) -> int:
    context.user_data["music_title"] = update.message.text
    await update.message.reply_text("Подтвердите заказ трека и оплату 1000 сом:", reply_markup=ReplyKeyboardMarkup([["OK","Отменить"]], one_time_keyboard=True))
    return MUSIC_CONFIRM

async def music_confirm(update, context) -> int:
    if update.message.text == "OK":
        title = context.user_data["music_title"]
        await update.message.reply_text("Трек заказан, спасибо!")
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = f"🎵 *Заказ музыки*\n▶️ {title}\n👤 {context.user_data['name']}\n⏰ {now}"
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg, parse_mode="Markdown")
    else:
        await update.message.reply_text("Отменено.")
    return MENU

# — Отзывы —
async def review_text(update, context) -> int:
    context.user_data["review_text"] = update.message.text
    kb = [["Анонимно","С именем"]]
    await update.message.reply_text("Как отправить отзыв?", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
    return REVIEW_ANON

async def review_anon(update, context) -> int:
    choice = update.message.text
    text = context.user_data["review_text"]
    if choice == "С именем":
        text = f"{context.user_data['name']}: {text}"
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text="💬 *Новый отзыв*\n" + text, parse_mode="Markdown")
    await update.message.reply_text("Спасибо за отзыв!")
    return MENU

# === Запуск приложения ===
    def main():
    # --- Тело функции main() обязательно с отступом ---
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    # Регистрируем хендлеры
    application.add_handler(CommandHandler("start", start))
    # … другие обработчики …

    return application  # возвращаем собранный экземпляр

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG:           [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_chosen)],
            NAME:           [MessageHandler(filters.TEXT & ~filters.COMMAND, name_chosen)],
            MENU:           [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
            BOOK_DATE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, book_date)],
            BOOK_TIME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, book_time)],
            BOOK_GUESTS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, book_guests)],
            BOOK_ZONE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, book_zone)],
            BOOK_CONFIRM:   [MessageHandler(filters.TEXT & ~filters.COMMAND, book_confirm)],
            AI_ALLERGY:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_allergy)],
            MUSIC_TITLE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, music_title)],
            MUSIC_CONFIRM:  [MessageHandler(filters.TEXT & ~filters.COMMAND, music_confirm)],
            REVIEW_TEXT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, review_text)],
            REVIEW_ANON:    [MessageHandler(filters.TEXT & ~filters.COMMAND, review_anon)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    
    # <-- здесь добавляете все ваши CommandHandler, CallbackQueryHandler и т.д.
    return application

 if __name__ == "__main__":
    # Получаем наш Application
    application = main()

    # Удаляем старый webhook (чтобы не было двойного получения апдейтов)
    application.bot.delete_webhook()

    # Запускаем polling
    # drop_pending_updates=True сбрасывает все «зависшие» апдейты,
    # чтобы бот начал с чистого листа
    application.run_polling(drop_pending_updates=True)
