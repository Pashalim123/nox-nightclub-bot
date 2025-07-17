import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования (можно смотреть логи в Render)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [
        ['🪑 Забронировать столик'],
        ['📋 Меню'],
        ['✍️ Оставить отзыв']
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}! Добро пожаловать в NOX Nightclub!",
        reply_markup=markup
    )

# Инициализация бота
app = Application.builder().token(os.getenv("BOT_TOKEN")).build()

# Обработчики
app.add_handler(CommandHandler("start", start))

# Запуск
app.run_polling()
