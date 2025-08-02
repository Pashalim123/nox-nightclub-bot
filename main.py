# main.py
import os
import logging
import asyncio
from datetime import datetime
from io import BytesIO

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from PIL import Image, ImageDraw

# Взять из .env группы Render или локального .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))  # например -1001234567890

# Константы для ConversationHandler
(
    LANG,
    ASK_NAME,
    MENU,
    BOOK_DATE,
    BOOK_TIME,
    BOOK_COUNT,
    BOOK_CONFIRM,
    AI_ALLERGY,
    AI_MENU,
    MUSIC_TITLE,
    MUSIC_CONFIRM,
    FEEDBACK_CHOICE,
    FEEDBACK_TEXT,
) = range(13)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Шаг 1: выбор языка
    kb = [["Русский"], ["English"]]
    await update.message.reply_text(
        "Выберите язык / Choose language:", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True)
    )
    return LANG


async def lang_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = update.message.text.lower()
    context.user_data["lang"] = "ru" if "рус" in lang else "en"
    # Шаг 2: имя
    q = "Как я могу к вам обращаться?" if context.user_data["lang"] == "ru" else "How may I call you?"
    await update.message.reply_text(q, reply_markup=ReplyKeyboardMarkup([["—"]], one_time_keyboard=True))
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    context.user_data["name"] = name
    # Главное меню
    texts = {
        "ru": f"Привет, {name}! Выберите раздел:",
        "en": f"Hello, {name}! Choose section:",
    }
    kb = [
        ["📅 Просмотреть меню", "🪑 Забронировать столик"],
        ["🤖 AI-меню", "🎵 Заказать музыку"],
        ["✍️ Оставить отзыв"],
    ]
    await update.message.reply_text(texts[context.user_data["lang"]], reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return MENU


# 3.1 — Бронирование
async def book_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # 3.1.1 — дата
    prompt = "Введите дату брони (ГГГГ-ММ-ДД):" if context.user_data["lang"] == "ru" else "Enter booking date (YYYY-MM-DD):"
    await update.message.reply_text(prompt)
    return BOOK_DATE


async def book_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["date"] = update.message.text.strip()
    prompt = "Введите время (ЧЧ:ММ):" if context.user_data["lang"] == "ru" else "Enter time (HH:MM):"
    await update.message.reply_text(prompt)
    return BOOK_TIME


async def book_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["time"] = update.message.text.strip()
    prompt = "Сколько гостей?" if context.user_data["lang"] == "ru" else "How many guests?"
    await update.message.reply_text(prompt)
    return BOOK_COUNT


async def book_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["count"] = update.message.text.strip()
    # 3.1.2 — схема зала
    img = draw_map(booked_seats=[])  # здесь можно передавать уже занятые столы
    await update.message.reply_photo(photo=img, caption="Выберите зону: VIP, Балкон, Танцпол, Бар")
    return BOOK_CONFIRM


async def book_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    zone = update.message.text.strip()
    data = context.user_data
    text = (
        f"Ваша бронь:\nДата: {data['date']}\nВремя: {data['time']}\nГостей: {data['count']}\nЗона: {zone}\n\n"
        "Подтвердить и перейти к предоплате? (да/нет)"
        if data["lang"] == "ru"
        else f"Your booking:\nDate: {data['date']}\nTime: {data['time']}\nGuests: {data['count']}\nZone: {zone}\n\nConfirm and prepay? (yes/no)"
    )
    await update.message.reply_text(text)
    # Сохранить зону для подтверждения
    context.user_data["zone"] = zone
    return BOOK_CONFIRM + 1  # состояние  BOOK_CONFIRM+1 == предоплата


async def book_prepay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ans = update.message.text.lower()
    if ans not in ("да", "yes"):
        await update.message.reply_text("Отменено." if context.user_data["lang"] == "ru" else "Cancelled.")
        return MENU
    # 3.1.4 — выдача QR (заглушка)
    qr = BytesIO()
    img = Image.new("RGB", (200, 200), "white")
    d = ImageDraw.Draw(img)
    d.text((20, 90), "QR-CODE", fill="black")
    img.save(qr, "PNG")
    qr.seek(0)
    await update.message.reply_photo(photo=qr, caption="Сканируйте для оплаты" if context.user_data["lang"] == "ru" else "Scan to pay")
    # Отправляем в группу
    summary = (
        f"Новая бронь от {context.user_data['name']}:\n"
        f"{data['date']} {data['time']}, {data['count']} guests, zone {data['zone']}"
        if context.user_data["lang"] == "ru"
        else f"New booking by {context.user_data['name']}:\n"
             f"{data['date']} {data['time']}, {data['count']} guests, zone {data['zone']}"
    )
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=summary)
    await update.message.reply_text("Спасибо! Бронь оформлена." if context.user_data["lang"] == "ru" else "Thank you! Booking confirmed.")
    return MENU


# 3.2 — AI-меню
async def ai_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prompt = "Есть ли у вас аллергии или продукты, которых вы избегаете? Если нет — напишите «нет»." if context.user_data["lang"] == "ru" else "Any allergies or forbidden ingredients? If no — type 'no'."
    await update.message.reply_text(prompt)
    return AI_ALLERGY


async def ai_allergy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["allergy"] = update.message.text.strip().lower()
    await update.message.reply_text("Формирую меню…" if context.user_data["lang"] == "ru" else "Building menu…")
    # Тут логика фильтрации — пока заглушка
    menu = ["Салат (зелень)", "Пицца (сыр, мука)", "Вино (виноград)"]
    filtered = [
        m for m in menu if context.user_data["allergy"] not in m.lower()
    ]
    out = "\n".join(filtered) or "Нет доступных позиций."
    await update.message.reply_text(out)
    return MENU


# 3.3 — Заказ музыки
async def music_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    prompt = "Введите название трека (доступные форматы: mp3, wav):"
    await update.message.reply_text(prompt)
    return MUSIC_TITLE


async def music_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    title = update.message.text.strip()
    context.user_data["track"] = title
    await update.message.reply_text("Отправляю запрос на оплату…")
    # Здесь должна быть интеграция платежей — пока заглушка
    await update.message.reply_text("Оплата прошла успешно!")
    # Отправка в группу
    dj = "DJ Nox"  # можно делать по расписанию
    msg = f"Заказ музыки: «{title}» от {context.user_data['name']} — DJ: {dj}"
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg)
    await update.message.reply_text("Трек принят в очередь." if context.user_data["lang"]=="ru" else "Track queued.")
    return MENU


# 3.4 — Отзыв
async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    kb = [["Анонимно"], ["С именем"]]
    await update.message.reply_text("Как оставить отзыв?", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
    return FEEDBACK_CHOICE


async def feedback_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["anon"] = update.message.text.startswith("Аноним")
    await update.message.reply_text("Напишите текст отзыва:")
    return FEEDBACK_TEXT


async def feedback_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    author = "Аноним" if context.user_data["anon"] else context.user_data["name"]
    msg = f"Новый отзыв от {author}:\n{text}"
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg)
    await update.message.reply_text("Спасибо за отзыв!" if context.user_data["lang"]=="ru" else "Thanks for feedback!")
    return MENU


# Хендлер, который кидает на нужный ConversationHandler
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    txt = update.message.text
    if "брони" in txt.lower() or "забронировать" in txt.lower():
        return await book_start(update, context)
    if "ai" in txt.lower() or "аллерг" in txt.lower():
        return await ai_start(update, context)
    if "музы" in txt.lower():
        return await music_start(update, context)
    if "отзыв" in txt.lower():
        return await feedback_start(update, context)
    if "меню" in txt.lower():
        # Просмотр меню — просто пример
        await update.message.reply_text("Наше меню:\n1) Салат\n2) Стейк\n3) Десерт")
        return MENU
    await update.message.reply_text("Не понял, выберите раздел.")
    return MENU


def draw_map(booked_seats: list) -> BytesIO:
    """
    Рисует схему зала 4×4 столов, закрашивая красным занятые, зелёным свободные.
    """
    sz = 400
    img = Image.new("RGB", (sz, sz), "white")
    d = ImageDraw.Draw(img)
    n = 4
    cell = sz // n
    for i in range(n):
        for j in range(n):
            x0, y0 = j * cell + 5, i * cell + 5
            x1, y1 = x0 + cell - 10, y0 + cell - 10
            idx = i * n + j
            color = "red" if idx in booked_seats else "green"
            d.rectangle([x0, y0, x1, y1], fill=color)
            d.text((x0 + 10, y0 + 10), f"{idx+1}", fill="white")
    bio = BytesIO()
    img.save(bio, "PNG")
    bio.seek(0)
    return bio


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # registration
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^(Русский|English)$"), lang_chosen))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu), group=1)

    # ConversationHandler не обязателен, мы рулим через main_menu
    # Но для чистоты можно сделать отдельными:
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🪑"), book_start)],
        states={
            BOOK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_date)],
            BOOK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_time)],
            BOOK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_count)],
            BOOK_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_confirm)],
            BOOK_CONFIRM + 1: [MessageHandler(filters.Regex("^(да|yes|нет|no)$"), book_prepay)],
        },
        fallbacks=[],
    )
    app.add_handler(conv)

    # AI
    app.add_handler(MessageHandler(filters.Regex("^(🤖|AI)"), ai_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_allergy), group=2)

    # Музыка
    app.add_handler(MessageHandler(filters.Regex("^(🎵|Заказать музыку)"), music_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, music_title), group=3)

    # Отзыв
    app.add_handler(MessageHandler(filters.Regex("^(✍️|Оставить отзыв)"), feedback_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_choice), group=4)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_text), group=5)

    # Запуск
    app.run_polling()


if __name__ == "__main__":
    main()
