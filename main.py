# main.py

import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ——————————————————————————————————————————————
# CONFIGURATION
# читаем токен и ID группы из переменных окружения
BOT_TOKEN     = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))

# включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# состояния сценария
LANG, ASK_NAME, MAIN_MENU, MUSIC_TRACK, MUSIC_CONFIRM = range(5)

# ——————————————————————————————————————————————
async def on_startup(app):
    """
    Удаляем любые старые webhook-и и сбрасываем несчитанные апдейты
    перед запуском polling.
    """
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhook deleted and pending updates dropped")

# ——————————————————————————————————————————————
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Команда /start — выбор языка."""
    keyboard = [["Русский"], ["English"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Выберите язык / Select language:", reply_markup=markup
    )
    return LANG

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняем выбор языка и запрашиваем имя."""
    text = update.message.text.strip().lower()
    context.user_data["lang"] = "ru" if text.startswith("р") else "en"
    prompt = "Как я могу к вам обращаться?" if context.user_data["lang"] == "ru" else "What is your name?"
    await update.message.reply_text(prompt)
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняем имя и показываем главное меню."""
    name = update.message.text.strip()
    context.user_data["name"] = name

    if context.user_data["lang"] == "ru":
        greeting = f"Привет, {name}! Добро пожаловать в NOX Nightclub!"
        keyboard = [["🪑 Забронировать столик"], ["🎵 Заказать музыку"], ["✍️ Оставить отзыв"]]
    else:
        greeting = f"Hello, {name}! Welcome to NOX Nightclub!"
        keyboard = [["🪑 Booking"], ["🎵 Music Order"], ["✍️ Feedback"]]

    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(greeting, reply_markup=markup)
    return MAIN_MENU

# ——————————————————————————————————————————————
# === ORDER MUSIC FLOW ===

async def order_music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашиваем название трека."""
    prompt = "Введите название трека:" if context.user_data["lang"] == "ru" else "Enter track name:"
    await update.message.reply_text(prompt)
    return MUSIC_TRACK

async def music_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняем трек и спрашиваем подтверждение."""
    context.user_data["track"] = update.message.text.strip()
    prompt = "Подтвердить заказ трека? (да/нет)" if context.user_data["lang"] == "ru" else "Confirm track order? (yes/no)"
    await update.message.reply_text(prompt)
    return MUSIC_CONFIRM

async def music_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Если да — шлём в группу, если нет — отменяем."""
    ans = update.message.text.strip().lower()
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
        # отправка в группу
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID, text=msg, parse_mode="HTML"
        )
        resp = "Ваш заказ принят!" if context.user_data["lang"] == "ru" else "Your order is confirmed!"
    else:
        resp = "Заказ отменен." if context.user_data["lang"] == "ru" else "Order cancelled."
    await update.message.reply_text(resp)
    return ConversationHandler.END

# ——————————————————————————————————————————————
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик /cancel."""
    text = "Отменено." if context.user_data.get("lang") == "ru" else "Cancelled."
    await update.message.reply_text(text)
    return ConversationHandler.END

# вспомогательный: вывести chat_id
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Chat ID = {update.effective_chat.id}")

# ——————————————————————————————————————————————
def main():
    # создаём приложение
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # конверсационный обработчик для музыки и меню
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG:          [MessageHandler(filters.TEXT & ~filters.COMMAND, set_language)],
            ASK_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            MAIN_MENU:     [
                MessageHandler(filters.Regex("Заказать музыку|Music Order"), order_music),
                # TODO: добавить другие пункты: бронирование, feedback, ai-menu
            ],
            MUSIC_TRACK:   [MessageHandler(filters.TEXT & ~filters.COMMAND, music_track)],
            MUSIC_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, music_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # регистрируем handlers
    app.add_handler(conv)
    app.add_handler(CommandHandler("id", get_id))

    # запускаем polling с pre-startup hook
    app.run_polling(on_startup=[on_startup])

if __name__ == "__main__":
    main()
