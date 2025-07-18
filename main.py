import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

LANGUAGE, BOOK_ZONE, BOOK_TABLE, BOOK_DATE, BOOK_TIME, BOOK_PEOPLE, CONFIRM = range(7)
user_lang = {}

zones = {
    "VIP": ["VIP-1", "VIP-2"],
    "Бар": ["Бар-1", "Бар-2"],
    "Танцпол": ["Танц-1", "Танц-2"],
    "Балкон": ["Балкон-1"]
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇷🇺 Русский", "🇬🇧 English"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите язык / Choose your language:", reply_markup=markup)
    return LANGUAGE

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.message.text
    user_lang[update.effective_user.id] = lang
    keyboard = [["🪑 Забронировать столик", "📋 Меню"], ["✍️ Оставить отзыв"]]
    await update.message.reply_text("Главное меню:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return ConversationHandler.END

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Наше меню:"
- Бургер: 400 KGS
- Коктейль: 300 KGS")

async def review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✍️ Напишите ваш отзыв:")

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={LANGUAGE: [MessageHandler(filters.TEXT, set_language)]},
    fallbacks=[]
))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("📋 Меню"), menu))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("✍️ Оставить отзыв"), review))
app.run_polling()
