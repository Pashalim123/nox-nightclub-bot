# main.py
import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# --- Чтение токена и ID группы из переменных окружения ---
BOT_TOKEN   = os.getenv("BOT_TOKEN")           # установлен в Render → Environment Variables
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))  # виден на скриншоте выше

# Состояния диалогов
LANG, ASK_NAME, MAIN_MENU, MUSIC_TRACK, MUSIC_CONFIRM = range(5)

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт бота: выбор языка."""
    kb = [["Русский"], ["English"]]
    markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Select language / Выберите язык:", reply_markup=markup)
    return LANG

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем язык и спрашиваем имя."""
    text = update.message.text.lower()
    context.user_data["lang"] = "ru" if text.startswith("р") or text.startswith("r") else "en"
    prompt = "Как я могу к вам обращаться?" if context.user_data["lang"]=="ru" else "What is your name?"
    await update.message.reply_text(prompt)
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем имя и показываем главное меню."""
    name = update.message.text.strip()
    context.user_data["name"] = name

    if context.user_data["lang"] == "ru":
        kb = [["Бронирование"], ["AI-Меню"], ["Заказать музыку"], ["Отзыв"]]
        greeting = f"Привет, {name}! Добро пожаловать в NOX Nightclub!"
    else:
        kb = [["Booking"], ["AI-Menu"], ["Music Order"], ["Feedback"]]
        greeting = f"Hello, {name}! Welcome to NOX Nightclub!"

    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text(greeting, reply_markup=markup)
    return MAIN_MENU

async def order_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 1: запрашиваем у гостя название трека."""
    prompt = "Введите название трека:" if context.user_data["lang"]=="ru" else "Enter track name:"
    await update.message.reply_text(prompt)
    return MUSIC_TRACK

async def music_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 2: сохраняем трек и спрашиваем подтверждение."""
    context.user_data["track"] = update.message.text.strip()
    prompt = "Подтвердить заказ трека? (да/нет)" if context.user_data["lang"]=="ru" else "Confirm track order? (yes/no)"
    await update.message.reply_text(prompt)
    return MUSIC_CONFIRM

async def music_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Шаг 3: по «да» отправляем в группу уведомление, по «нет» – отменяем."""
    ans = update.message.text.strip().lower()
    if ans in ("да", "yes"):
        name  = context.user_data["name"]
        track = context.user_data["track"]
        dj    = "DJ Example"  # можно подставить расписание по дню недели
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M")
        group_msg = (
            f"🎵 <b>Заказ музыки</b>\n"
            f"Гость: {name}\n"
            f"Трек: {track}\n"
            f"DJ: {dj}\n"
            f"Время: {ts}"
        )
        # <-- вот где происходит отправка в Telegram-группу
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=group_msg,
            parse_mode="HTML"
        )
        resp = "Ваш заказ принят!" if context.user_data["lang"]=="ru" else "Your order is confirmed!"
    else:
        resp = "Заказ отменен." if context.user_data["lang"]=="ru" else "Order cancelled."
    await update.message.reply_text(resp)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общий handler для /cancel."""
    text = "Отменено." if context.user_data.get("lang")=="ru" else "Cancelled."
    await update.message.reply_text(text)
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Конверсационный handler для /start → выбор языка → имя → меню → музыка
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG:          [MessageHandler(filters.TEXT & ~filters.COMMAND, set_language)],
            ASK_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            MAIN_MENU:     [
                MessageHandler(filters.Regex("Заказать музыку|Music Order"), order_music),
                # сюда можно добавить другие пункты меню
            ],
            MUSIC_TRACK:   [MessageHandler(filters.TEXT & ~filters.COMMAND, music_track)],
            MUSIC_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, music_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Хэндлер для отладки – показывает chat_id любого чата
    async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"Chat ID = {update.effective_chat.id}")

    app.add_handler(conv)
    app.add_handler(CommandHandler("id", get_id))

    app.run_polling()

if __name__ == "__main__":
    main()
