
import os
import logging
from datetime import datetime
from io import BytesIO

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

# ————— Настройка логирования —————
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ————— Состояния —————
(
    LANG, ASK_NAME, MENU,
    BOOK_START, BOOK_DATE, BOOK_TIME, BOOK_COUNT, BOOK_ZONE, BOOK_CONFIRM, BOOK_PREPAY,
    AI_START, AI_ALLERGY,
    MUSIC_START, MUSIC_TITLE, MUSIC_CONFIRM,
    FB_START, FB_CHOICE, FB_TEXT
) = range(18)

# ————— Чтение конфига —————
BOT_TOKEN    = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))

# ————— /start → выбор языка —————
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    kb = [["🇷🇺 Русский"], ["🇬🇧 English"]]
    await update.message.reply_text(
        "Выберите язык / Choose language:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return LANG

async def lang_chosen(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.lower()
    ctx.user_data["lang"] = "ru" if "рус" in choice else "en"
    prompt = "Как я могу к вам обращаться?" if ctx.user_data["lang"]=="ru" else "What is your name?"
    await update.message.reply_text(prompt, reply_markup=ReplyKeyboardRemove())
    return ASK_NAME

async def ask_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["name"] = update.message.text.strip()
    name = ctx.user_data["name"]
    lang = ctx.user_data["lang"]
    greeting = f"Привет, {name}! Выберите раздел:" if lang=="ru" else f"Hello, {name}! Choose section:"
    kb = [
        ["📅 Просмотреть меню", "🪑 Забронировать столик"],
        ["🤖 AI-меню",      "🎵 Заказать музыку"],
        ["✍️ Оставить отзыв"]
    ]
    await update.message.reply_text(greeting,
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return MENU

# ————— Главное меню маршрутизация —————
async def menu_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    txt = update.message.text
    lang = ctx.user_data["lang"]
    if "🪑" in txt:
        return await book_start(update, ctx)
    if "AI" in txt or "🤖" in txt:
        return await ai_start(update, ctx)
    if "🎵" in txt:
        return await music_start(update, ctx)
    if "✍️" in txt:
        return await fb_start(update, ctx)
    if "📅" in txt:
        menu = "1) Салат\n2) Стейк\n3) Десерт" if lang=="ru" else "1) Salad\n2) Steak\n3) Dessert"
        await update.message.reply_text(menu)
        return MENU
    await update.message.reply_text("Не понял, выберите пункт меню.")
    return MENU

# ————— 3.1 Бронирование —————
async def book_start(update, ctx) -> int:
    prompt = "Введите дату бронирования (YYYY-MM-DD):" if ctx.user_data["lang"]=="ru" else "Enter booking date (YYYY-MM-DD):"
    await update.message.reply_text(prompt, reply_markup=ReplyKeyboardRemove())
    return BOOK_DATE

async def book_date(update, ctx) -> int:
    ctx.user_data["date"] = update.message.text.strip()
    prompt = "Введите время (HH:MM):" if ctx.user_data["lang"]=="ru" else "Enter time (HH:MM):"
    await update.message.reply_text(prompt)
    return BOOK_TIME

async def book_time(update, ctx) -> int:
    ctx.user_data["time"] = update.message.text.strip()
    prompt = "Сколько гостей?" if ctx.user_data["lang"]=="ru" else "How many guests?"
    await update.message.reply_text(prompt)
    return BOOK_COUNT

async def book_count(update, ctx) -> int:
    ctx.user_data["count"] = update.message.text.strip()
    # Показ схемы зала
    img_io = draw_map(booked_seats=[])
    await update.message.reply_photo(photo=img_io, caption="Зал: 🟢 свободно, 🔴 занято")
    prompt = "Выберите зону: VIP, Балкон, Танцпол, Бар" if ctx.user_data["lang"]=="ru" else "Choose zone: VIP, Balcony, Dancefloor, Bar"
    await update.message.reply_text(prompt)
    return BOOK_ZONE

async def book_zone(update, ctx) -> int:
    ctx.user_data["zone"] = update.message.text.strip()
    d = ctx.user_data; lang = d["lang"]
    summary = f"Дата: {d['date']}\nВремя: {d['time']}\nГостей: {d['count']}\nЗона: {d['zone']}"
    prompt = "Подтвердить бронь и оплатить 1000 сом? (да/нет)" if lang=="ru" else "Confirm and pay 1000 som? (yes/no)"
    await update.message.reply_text(summary + "\n" + prompt)
    return BOOK_CONFIRM

async def book_confirm(update, ctx) -> int:
    ans = update.message.text.strip().lower()
    lang = ctx.user_data["lang"]
    if ans in ("да","yes"):
        # Заглушка QR
        qr = BytesIO()
        from PIL import ImageDraw, Image
        im = Image.new("RGB",(200,200),"white")
        ImageDraw.Draw(im).text((50,90),"QR CODE","black")
        im.save(qr,"PNG"); qr.seek(0)
        await update.message.reply_photo(photo=qr, caption="Сканируйте для оплаты")
        # Уведомление
        d = ctx.user_data
        msg = f"Новая бронь: {d['date']} {d['time']}, {d['count']} guests, zone {d['zone']} by {d['name']}"
        await ctx.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg)
        await update.message.reply_text("Бронь оформлена!" if lang=="ru" else "Booking complete!")
    else:
        await update.message.reply_text("Отменено." if lang=="ru" else "Cancelled.")
    return MENU

# ————— 3.2 AI-меню —————
async def ai_start(update, ctx) -> int:
    prompt = "Есть ли у вас аллергии? Перечислите или 'нет'." if ctx.user_data["lang"]=="ru" else "Any allergies? List or 'no'."
    await update.message.reply_text(prompt, reply_markup=ReplyKeyboardRemove())
    return AI_ALLERGY

async def ai_allergy(update, ctx) -> int:
    al = update.message.text.lower().split(",")
    # Фильтрация (пример)
    full = ["Салат", "Пицца", "Стейк"]
    filtered = [x for x in full if not any(a in x.lower() for a in al)]
    await update.message.reply_text("\n".join(filtered) or "Нет доступных" if ctx.user_data["lang"]=="ru" else "\n".join(filtered) or "No items")
    return MENU

# ————— 3.3 Заказ музыки —————
async def music_start(update, ctx) -> int:
    prompt = "Введите название трека:" if ctx.user_data["lang"]=="ru" else "Enter track title:"
    await update.message.reply_text(prompt, reply_markup=ReplyKeyboardRemove())
    return MUSIC_TITLE

async def music_title(update, ctx) -> int:
    ctx.user_data["track"] = update.message.text.strip()
    # Заглушка оплаты
    await update.message.reply_text("Оплата 500 сом… (заглушка)")
    # Уведомление
    dj = "DJ Nox"
    msg = f"Заказ музыки: {ctx.user_data['track']} | DJ: {dj} | by {ctx.user_data['name']}"
    await ctx.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg)
    await update.message.reply_text("Трек заказан!" if ctx.user_data["lang"]=="ru" else "Track ordered!")
    return MENU

# ————— 3.4 Отзыв —————
async def fb_start(update, ctx) -> int:
    kb = [["Анонимно"],["С именем"]]
    await update.message.reply_text("Анонимно или с именем?", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True))
    return FB_CHOICE

async def fb_choice(update, ctx) -> int:
    ctx.user_data["anon"] = update.message.text.startswith("Аноним")
    await update.message.reply_text("Напишите отзыв:", reply_markup=ReplyKeyboardRemove())
    return FB_TEXT

async def fb_text(update, ctx) -> int:
    text = update.message.text.strip()
    author = "Аноним" if ctx.user_data["anon"] else ctx.user_data["name"]
    msg = f"Отзыв от {author}: {text}"
    await ctx.bot.send_message(chat_id=GROUP_CHAT_ID, text=msg)
    await update.message.reply_text("Спасибо за отзыв!")
    return MENU

# ————— ОТМЕНА —————
async def cancel(update, ctx) -> int:
    await update.message.reply_text("Операция отменена.", reply_markup=ReplyKeyboardRemove())
    return MENU

# ————— Основная функция —————
def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Очистка webhook перед polling
    app.bot.delete_webhook(drop_pending_updates=True)

    # Общие хендлеры
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("🇷🇺|🇬🇧"), lang_chosen))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_router), group=1)

    # ConversationHandlers
    book_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🪑"), book_start)],
        states={
            BOOK_DATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, book_date)],
            BOOK_TIME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, book_time)],
            BOOK_COUNT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, book_count)],
            BOOK_ZONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, book_zone)],
            BOOK_CONFIRM:[MessageHandler(filters.Regex("^(да|yes|нет|no)$"), book_confirm)],
        }, fallbacks=[CommandHandler("cancel", cancel)], per_user=True
    )
    app.add_handler(book_conv)

    ai_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🤖"), ai_start)],
        states={AI_ALLERGY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_allergy)]},
        fallbacks=[CommandHandler("cancel", cancel)], per_user=True
    )
    app.add_handler(ai_conv)

    music_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("🎵"), music_start)],
        states={MUSIC_TITLE:[MessageHandler(filters.TEXT & ~filters.COMMAND, music_title)]},
        fallbacks=[CommandHandler("cancel", cancel)], per_user=True
    )
    app.add_handler(music_conv)

    fb_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("✍️"), fb_start)],
        states={
            FB_CHOICE:[MessageHandler(filters.TEXT & ~filters.COMMAND, fb_choice)],
            FB_TEXT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, fb_text)]
        },
        fallbacks=[CommandHandler("cancel", cancel)], per_user=True
    )
    app.add_handler(fb_conv)

    # Запуск
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
