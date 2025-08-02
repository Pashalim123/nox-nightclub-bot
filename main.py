# main.py

import os
import logging
from datetime import datetime

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from draw_map import draw_map

# ==== Настройка логов ====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==== Константы состояний ====
(
    LANG, ASK_NAME, MENU,
    BOOK_DATE, BOOK_TIME, BOOK_COUNT, BOOK_TABLE, BOOK_CONFIRM,
    AI_ALLERGY, AI_MENU,
    MUSIC_REQUEST, MUSIC_CONFIRM,
    REVIEW_CHOOSE, REVIEW_TEXT,
) = range(14)

# Схема зала — координаты столиков на карте (пример)
SEAT_COORDS = {
    1: (100, 200),
    2: (100, 350),
    3: (100, 500),
    4: (400, 350),
}

# ID группы для уведомлений
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))
# Ссылка на оплату предоплаты/треков (заглушка)
PAYMENT_LINK = "https://example.com/pay?amount="

# ==== /start ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    kb = [["Русский", "English"]]
    await update.message.reply_text(
        "Выберите язык / Choose language:", 
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return LANG

async def choose_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = update.message.text.lower()
    context.user_data["lang"] = "ru" if "рус" in lang else "en"
    await update.message.reply_text(
        {"ru": "Как к вам обращаться?", "en": "What is your name?"}[context.user_data["lang"]],
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    context.user_data["name"] = name
    # Главное меню
    kb = [
        ["🪑 Забронировать столик", "📅 AI-меню"],
        ["🎵 Заказать музыку", "✍️ Оставить отзыв"],
    ]
    await update.message.reply_text(
        f"{name}, добро пожаловать! Что выберем?",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return MENU

# ==== МЕНЮ ====
async def menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if "забронир" in text.lower():
        await update.message.reply_text("Введите дату брони (YYYY-MM-DD):")
        return BOOK_DATE
    if "ai" in text.lower() or "меню" in text.lower():
        await update.message.reply_text("Есть ли у вас аллергии? Перечислите ингредиенты, или напишите `нет`.")
        return AI_ALLERGY
    if "музык" in text.lower():
        await update.message.reply_text("Какой трек хотите заказать? (House/Pop/RnB/Techno)")
        return MUSIC_REQUEST
    if "отзыв" in text.lower():
        await update.message.reply_text("Введите ваш отзыв:")
        return REVIEW_TEXT
    await update.message.reply_text("Пожалуйста, выберите пункт меню.")
    return MENU

# ==== БРОНИРОВАНИЕ ====
async def book_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["date"] = update.message.text.strip()
    await update.message.reply_text("Введите время (HH:MM):")
    return BOOK_TIME

async def book_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["time"] = update.message.text.strip()
    await update.message.reply_text("Сколько гостей?")
    return BOOK_COUNT

async def book_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["count"] = update.message.text.strip()
    # Предполагаем 4 стола
    kb = [[KeyboardButton(f"Стол {i}")] for i in SEAT_COORDS.keys()]
    await update.message.reply_text("Выберите столик:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return BOOK_TABLE

async def book_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Извлекаем номер столика
    table = int(update.message.text.replace("Стол ", ""))
    context.user_data["table"] = table
    # Подтверждение
    d = context.user_data["date"]
    t = context.user_data["time"]
    c = context.user_data["count"]
    tb = context.user_data["table"]
    await update.message.reply_text(
        f"Вы выбрали:\nДата: {d}\nВремя: {t}\nГостей: {c}\nСтол: {tb}\nПодтвердить? (да/нет)",
        reply_markup=ReplyKeyboardMarkup([["да","нет"]], resize_keyboard=True)
    )
    return BOOK_CONFIRM

async def book_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ans = update.message.text.lower()
    if ans != "да":
        await update.message.reply_text("Бронирование отменено.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # Генерация карты
    # Собираем простой статус: занятое — только что занят.
    reservations = {i: (i == context.user_data["table"]) for i in SEAT_COORDS}
    map_file = draw_map(reservations, base_path="hall_base.png", out_path="hall_map.png")

    # Отправляем гостю
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open(map_file, "rb"),
        caption="Схема зала: 🔴 занято, 🟢 свободно",
        reply_markup=ReplyKeyboardRemove()
    )

    # Уведомление в группу
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = (
        f"🪑 <b>Новая бронь</b>\n"
        f"Гость: {context.user_data['name']}\n"
        f"Дата/Время: {context.user_data['date']} {context.user_data['time']}\n"
        f"Гостей: {context.user_data['count']}\n"
        f"Стол: {context.user_data['table']}\n"
        f"Время: {ts}"
    )
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=msg,
        parse_mode="HTML"
    )

    await update.message.reply_text("Ваша бронь подтверждена! Спасибо.")
    return ConversationHandler.END

# ==== AI-МЕНЮ ====
async def ai_allergy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["allergy"] = update.message.text.strip().lower()
    # Заглушка: просто отдаем меню
    menu_text = (
        "Наше меню:\n"
        "- Кесадилья с курицей\n"
        "- Пицца Маргарита\n"
        "- Салат Цезарь\n"
        # ...
    )
    await update.message.reply_text(menu_text, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ==== ЗАКАЗ МУЗЫКИ ====
async def music_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["track"] = update.message.text.strip()
    await update.message.reply_text(
        f"Вы заказываете: {context.user_data['track']}\n"
        "Сумма 1000 KGS. Оплатить? (да/нет)"
    )
    return MUSIC_CONFIRM

async def music_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == "да":
        link = PAYMENT_LINK + "1000"
        await update.message.reply_text(f"Ссылка для оплаты: {link}")
        # После оплаты (вручную) администратор нажимает кнопку, но у нас просто уведомляем сразу:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=f"🎵 Заказ музыки: {context.user_data['track']} от {context.user_data['name']}"
        )
        await update.message.reply_text("Спасибо! Ваш заказ получен.")
    else:
        await update.message.reply_text("Заказ отменён.")
    return ConversationHandler.END

# ==== ОСТАВИТЬ ОТЗЫВ ====
async def review_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    review = update.message.text.strip()
    anon = False
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=(
            f"✍️ Отзыв\n"
            f"{'(аноним)' if anon else context.user_data['name']}: {review}"
        )
    )
    await update.message.reply_text("Спасибо за ваш отзыв!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ==== ОТМЕНА ====
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Операция отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ==== Основная функция ====
def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_lang)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_choice)],

            BOOK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_date)],
            BOOK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_time)],
            BOOK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_count)],
            BOOK_TABLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_table)],
            BOOK_CONFIRM: [MessageHandler(filters.Regex("^(да|нет)$"), book_confirm)],

            AI_ALLERGY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_allergy)],

            MUSIC_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, music_request)],
            MUSIC_CONFIRM: [MessageHandler(filters.Regex("^(да|нет)$"), music_confirm)],

            REVIEW_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
