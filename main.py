from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [['Забронировать столик'], ['Меню'], ['Оставить отзыв']]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}! Добро пожаловать в NOX Nightclub!",
        reply_markup=markup
    )

import os
application = Application.builder().token(os.getenv("BOT_TOKEN")).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
