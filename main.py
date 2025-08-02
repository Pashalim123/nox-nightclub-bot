import os
import logging
import requests
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ——————————————————————————————————————————————
# CONFIGURATION
BOT_TOKEN     = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation states
LANG, ASK_NAME, MAIN_MENU, MUSIC_TRACK, MUSIC_CONFIRM = range(5)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["Русский"], ["English"]]
    await update.message.reply_text(
        "Выберите язык / Select language:", 
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return LANG


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    context.user_data["lang"] = "ru" if text.startswith("р") else "en"
    prompt = (
        "Как я могу к вам обращаться?" 
        if context.user_data["lang"] == "ru"
        else "What is your name?"
    )
    await update.message.reply_text(prompt)
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    context.user_data["name"] = name

    if context.user_data["lang"] == "ru":
        text = f"Привет, {name}! Добро пожаловать в NOX Nightclub!"
        keyboard = [["🪑 Забронировать столик"], ["🎵 Заказать музыку"], ["✍️ Оставить отзыв"]]
    else:
        text = f"Hello, {name}! Welcome to NOX Nightclub!"
        keyboard = [["🪑 Booking"], ["🎵 Music Order"], ["✍️ Feedback"]]

    await update.message.reply_text(
        text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MAIN_MENU


async def order_music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prompt = (
        "Введите название трека:" 
        if context.user_data["lang"] == "ru"
        else "Enter track name:"
    )
    await update.message.reply_text(prompt)
    return MUSIC_TRACK


async def music_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["track"] = update.message.text.strip()
    prompt = (
        "Подтвердить заказ трека? (да/нет)"
        if context.user_data["lang"] == "ru"
        else "Confirm track order? (yes/no)"
    )
    await update.message.reply_text(prompt)
    return MUSIC_CONFIRM


async def music_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ans = update.message.text.lower()
    if ans in ("да", "yes"):
        name  = context.user_data["name"]
        track = context.user_data["track"]
        dj    = "DJ Example"  # TODO: динамически по расписанию
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = (
            f"🎵 <b>Заказ музыки</b>\n"
            f"Гость: {name}\n"
            f"Трек: {track}\n"
            f"DJ: {dj}\n"
            f"Время: {ts}"
        )
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID, text=msg, parse_mode="HTML"
        )
        resp = "Ваш заказ принят!" if context.user_data["lang"] == "ru" else "Your order is confirmed!"
    else:
        resp = "Заказ отменён." if context.user_data["lang"] == "ru" else "Order cancelled."
    await update.message.reply_text(resp)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "Отменено." if context.user_data.get("lang") == "ru" else "Cancelled."
    await update.message.reply_text(text)
    return ConversationHandler.END


async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Chat ID = {update.effective_chat.id}")


def main():
    # 1) Сброс webhook (sync HTTP-запрос до старта polling)
    delete_url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}"
        f"/deleteWebhook?drop_pending_updates=true"
    )
    resp = requests.get(delete_url)
    logger.info("DeleteWebhook response: %s", resp.text)

    # 2) Собираем приложение
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG:          [MessageHandler(filters.TEXT & ~filters.COMMAND, set_language)],
            ASK_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            MAIN_MENU:     [
                MessageHandler(filters.Regex("Заказать музыку|Music Order"), order_music),
                # TODO: добавить другие пункты
            ],
            MUSIC_TRACK:   [MessageHandler(filters.TEXT & ~filters.COMMAND, music_track)],
            MUSIC_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, music_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("id", get_id))

    # 3) Запускаем polling с автоматическим сбросом pending_updates
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
