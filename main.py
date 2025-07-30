import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

logging.basicConfig(level=logging.INFO)

# States for conversation
LANGUAGE, BOOK_ZONE, BOOK_TABLE, BOOK_DATETIME, BOOK_PEOPLE = range(5)

# In-memory user data
user_data = {}

# Seats configuration
seats = {
    "VIP": ["VIP-1", "VIP-2"],
    "Балкон": ["Балкон-1", "Балкон-2"],
    "Танцпол": ["Танцпол-1", "Танцпол-2"],
    "Бар": ["Бар-1", "Бар-2"]
}

# Texts for languages
texts = {
    "ru": {
        "select_lang": "Выберите язык / Choose language:",
        "main_menu": "Главное меню:",
        "menu": "📋 Меню:\n- Бургер: 400 KGS\n- Коктейль: 300 KGS",
        "review": "✍️ Напишите ваш отзыв:",
        "ask_zone": "🪑 Выберите зону для бронирования:",
        "ask_table": "📍 Выберите столик в зоне {zone}:",
        "ask_datetime": "🗓 Введите дату и время (например: 2025-07-20 20:00):",
        "ask_people": "👥 Введите количество гостей:",
        "confirm": "✅ Бронь: зона {zone}, столик {table}, время {datetime}, гостей {people}.",
        "cancel": "❌ Бронирование отменено."
    },
    "en": {
        "select_lang": "Select language / Выберите язык:",
        "main_menu": "Main menu:",
        "menu": "📋 Menu:\n- Burger: 400 KGS\n- Cocktail: 300 KGS",
        "review": "✍️ Please write your review:",
        "ask_zone": "🪑 Select zone to book:",
        "ask_table": "📍 Select table in zone {zone}:",
        "ask_datetime": "🗓 Enter date and time (e.g.: 2025-07-20 20:00):",
        "ask_people": "👥 Enter number of guests:",
        "confirm": "✅ Booking: zone {zone}, table {table}, time {datetime}, guests {people}.",
        "cancel": "❌ Booking cancelled."
    }
}

def get_lang(user_id):
    return user_data.get(user_id, {}).get("lang", "ru")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇷🇺 Русский", "🇬🇧 English"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(texts["ru"]["select_lang"], reply_markup=markup)
    return LANGUAGE

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_choice = update.message.text
    lang = "ru" if "🇷🇺" in lang_choice else "en"
    user_id = update.effective_user.id
    user_data[user_id] = {"lang": lang}
    # Main menu
    menu_buttons = [["📋 Меню", "🪑 Забронировать столик"], ["✍️ Оставить отзыв"]] if lang == "ru" else [["Menu", "Book table"], ["Review"]]
    markup = ReplyKeyboardMarkup(menu_buttons, resize_keyboard=True)
    await update.message.reply_text(texts[lang]["main_menu"], reply_markup=markup)
    return ConversationHandler.END

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    await update.message.reply_text(texts[lang]["menu"])

async def leave_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    await update.message.reply_text(texts[lang]["review"])

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    zones = list(seats.keys())
    keyboard = [[z] for z in zones]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(texts[lang]["ask_zone"], reply_markup=markup)
    return BOOK_ZONE

async def choose_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    zone = update.message.text
    context.user_data["zone"] = zone
    lang = get_lang(user_id)
    tables = seats.get(zone, [])
    keyboard = [[t] for t in tables]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(texts[lang]["ask_table"].format(zone=zone), reply_markup=markup)
    return BOOK_TABLE

async def choose_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    table = update.message.text
    context.user_data["table"] = table
    lang = get_lang(user_id)
    await update.message.reply_text(texts[lang]["ask_datetime"])
    return BOOK_DATETIME

async def choose_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    datetime = update.message.text
    context.user_data["datetime"] = datetime
    lang = get_lang(user_id)
    await update.message.reply_text(texts[lang]["ask_people"])
    return BOOK_PEOPLE

async def choose_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    people = update.message.text
    data = context.user_data
    zone = data.get("zone")
    table = data.get("table")
    datetime = data.get("datetime")
    locals_ = {"zone": zone, "table": table, "datetime": datetime, "people": people}
    lang = get_lang(user_id)
    confirm_msg = texts[lang]["confirm"].format(**locals_)
    await update.message.reply_text(confirm_msg)
    # send to group
    group_id = os.getenv("GROUP_CHAT_ID")
    await context.bot.send_message(chat_id=group_id, text=confirm_msg)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    await update.message.reply_text(texts[lang]["cancel"])
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🪑 Забронировать столик") | filters.Regex("Book table"), start_booking)],
        states={
            BOOK_ZONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_zone)],
            BOOK_TABLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_table)],
            BOOK_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_datetime)],
            BOOK_PEOPLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_people)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.Regex("📋 Меню") | filters.Regex("Menu"), show_menu))
    application.add_handler(MessageHandler(filters.Regex("✍️ Оставить отзыв") | filters.Regex("Review"), leave_review))
    application.run_polling()

if __name__ == "__main__":
    main()