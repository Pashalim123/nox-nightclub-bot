import os
import logging
from datetime import datetime
from telegram import (
    Update, ReplyKeyboardMarkup, InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler,
    ContextTypes, filters
)

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
(
    LANG, ASK_NAME,
    MENU, BOOK_DATE, BOOK_PEOPLE,
    BOOK_ZONE, BOOK_TABLE, BOOK_CONFIRM,
    AI_ALLERGY,
    MUSIC_NAME, MUSIC_CONFIRM,
    REVIEW_CHOICE, REVIEW_TEXT
) = range(13)

# В памяти хранение
users = {}        # user_id → {lang, name, allergy}
reservations = [] # список бронирований
seats = {
    "VIP": ["VIP-1","VIP-2","VIP-3"],
    "Балкон": ["Б-1","Б-2"],
    "Танцпол": ["Т-1","Т-2","Т-3"],
    "Бар": ["Бар-1"]
}
dishes = [
    {"name":"Бургер","ingredients":["мясо","сыр"]},
    {"name":"Салат Цезарь","ingredients":["майонез","сыр","курица"]},
    {"name":"Мохито","ingredients":["мята","лайм"]},
    {"name":"Паста","ingredients":["паста","сыр"]}
]
dj_schedule = {
    0:"DJ Alpha",1:"DJ Beta",2:"DJ Gamma",
    3:"DJ Delta",4:"DJ Epsilon",5:"DJ Zeta",6:"DJ Eta"
}

# Тексты на двух языках
texts = {
  "ru": {
    "select_lang":"Выберите язык:",
    "ask_name":"Как я могу к вам обращаться?",
    "main_menu":"Главное меню:",
    "menu":"📋 Меню:\n- "+"\n- ".join(d["name"] for d in dishes),
    "review":"✍️ Напишите ваш отзыв:",
    "ask_allergy":"Укажите аллергию (через запятую):",
    "ai_menu":"🍽️ Меню (отфильтровано):\n",
    "ask_date":"🗓 Дата и время (YYYY-MM-DD HH:MM):",
    "ask_people":"👥 Количество гостей?",
    "ask_zone":"🪑 Выберите зону:",
    "ask_table":"📍 Выберите столик в зоне {zone}:",
    "confirm_booking":"✅ Бронь: зона {zone}, столик {table}, время {datetime}, гостей {people}.\nПредоплата 1000 сом.",
    "cancel":"❌ Отменено.",
    "music_warn":"⚠️ Жанры: House, Pop, RnB, Techno",
    "music_prompt":"🎵 Название трека:",
    "music_confirm":"Подтвердите заказ '{track}' за 1000 сом? (да/нет)",
    "thank_you":"Спасибо! Админ уведомлён.",
    "review_thanks":"Спасибо за отзыв!"
  },
  "en": {
    "select_lang":"Select language:",
    "ask_name":"How shall I call you?",
    "main_menu":"Main menu:",
    "menu":"📋 Menu:\n- "+"\n- ".join(d["name"] for d in dishes),
    "review":"✍️ Please write your review:",
    "ask_allergy":"List allergies (comma-separated):",
    "ai_menu":"🍽️ Menu (filtered):\n",
    "ask_date":"🗓 Date & time (YYYY-MM-DD HH:MM):",
    "ask_people":"👥 Number of guests?",
    "ask_zone":"🪑 Select zone:",
    "ask_table":"📍 Select table in {zone}:",
    "confirm_booking":"✅ Booking: zone {zone}, table {table}, time {datetime}, guests {people}.\nPrepay 1000 som.",
    "cancel":"❌ Cancelled.",
    "music_warn":"⚠️ Genres: House, Pop, RnB, Techno",
    "music_prompt":"🎵 Track name:",
    "music_confirm":"Confirm order '{track}' for 1000 som? (yes/no)",
    "thank_you":"Thank you! Admin notified.",
    "review_thanks":"Thank you for your feedback!"
  }
}

def t(user_id, key):
    lang = users.get(user_id,{}).get("lang","ru")
    return texts[lang][key]

# /start → выбор языка
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users[uid]={}
    kb = [["Русский","English"]]
    await update.message.reply_text(texts["ru"]["select_lang"],
        reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True,one_time_keyboard=True))
    return LANG

# Установить язык → спросить имя
async def set_lang(update, ctx):
    uid=update.effective_user.id
    choice=update.message.text
    users[uid]["lang"]="ru" if choice.startswith("Рус") else "en"
    await update.message.reply_text(t(uid,"ask_name"))
    return ASK_NAME

# Установить имя → показать меню
async def set_name(update, ctx):
    uid=update.effective_user.id
    users[uid]["name"]=update.message.text
    # кнопки меню
    lang=users[uid]["lang"]
    kb = [
      ["🪑 Бронирование" if lang=="ru" else "Book table","📋 Меню" if lang=="ru" else "Menu"],
      ["🤖 AI-меню","🎵 Заказать музыку"],["✍️ Отзыв"]
    ]
    await update.message.reply_text(t(uid,"main_menu"),
        reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True))
    return MENU

# Обработка выбора в меню
async def menu_choice(update, ctx):
    uid=update.effective_user.id
    txt=update.message.text
    # Бронирование
    if "🪑" in txt or "Book" in txt:
        await update.message.reply_text(t(uid,"ask_date"))
        return BOOK_DATE
    # Меню
    if "📋" in txt or txt=="Menu":
        await update.message.reply_text(t(uid,"menu"))
        return MENU
    # AI-меню
    if "AI" in txt:
        await update.message.reply_text(t(uid,"ask_allergy"))
        return AI_ALLERGY
    # Музыка
    if "🎵" in txt or "Track" in txt:
        await update.message.reply_text(t(uid,"music_warn"))
        await update.message.reply_text(t(uid,"music_prompt"))
        return MUSIC_NAME
    # Отзыв
    if "✍️" in txt or "Review" in txt:
        kb=[["Анонимно","С именем"]]
        await update.message.reply_text(t(uid,"review"),
            reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True,one_time_keyboard=True))
        return REVIEW_CHOICE
    return MENU

# Бронирование: дата → гости → зона → стол → подтверждение
async def book_date(update, ctx):
    uid=update.effective_user.id
    txt=update.message.text
    try:
        datetime.strptime(txt,"%Y-%m-%d %H:%M")
    except:
        await update.message.reply_text("Неверный формат, повторите")
        return BOOK_DATE
    ctx.user_data["datetime"]=txt
    await update.message.reply_text(t(uid,"ask_people"))
    return BOOK_PEOPLE

async def book_people(update, ctx):
    uid=update.effective_user.id
    ctx.user_data["people"]=update.message.text
    # зоны
    kb=[[z] for z in seats]
    await update.message.reply_text(t(uid,"ask_zone"),
        reply_markup=ReplyKeyboardMarkup(kb,one_time_keyboard=True,resize_keyboard=True))
    return BOOK_ZONE

async def book_zone(update, ctx):
    uid=update.effective_user.id
    zone=update.message.text
    ctx.user_data["zone"]=zone
    # столики inline
    buttons=[]
    for tbl in seats[zone]:
        taken=any(r["table"]==tbl for r in reservations)
        emoji="🔴" if taken else "🟢"
        buttons.append(InlineKeyboardButton(f"{tbl} {emoji}",callback_data=f"tbl|{tbl}"))
    kb=[buttons[i:i+2] for i in range(0,len(buttons),2)]
    await update.message.reply_text(t(uid,"ask_table").format(zone=zone),
        reply_markup=InlineKeyboardMarkup(kb))
    return BOOK_TABLE

async def book_table_cb(update, ctx):
    await update.callback_query.answer()
    uid=update.callback_query.from_user.id
    _,tbl=update.callback_query.data.split("|")
    ctx.user_data["table"]=tbl
    await update.callback_query.edit_message_text(t(uid,"confirm_booking").format(**ctx.user_data))
    # сохраняем и уведомляем
    
    data=ctx.user_data; data["name"]=users[uid]["name"]
    reservations.append(data.copy())
    await ctx.bot.send_message(
        chat_id=os.getenv("-1002705399393"),
        text=f"Новая бронь: {data}"
    )
    return ConversationHandler.END
# Пример для брони (внутри функции confirm_booking)
# после формирования текста confirm_text:
confirm_text = texts[lang]["confirm_booking"].format(**ctx.user_data)
# Добавим дату создания и имя гостя
from datetime import datetime
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
guest = users[uid]["name"]
group_msg = (
    f"🆕 <b>Новая бронь</b>\n"
    f"Гость: {guest}\n"
    f"Дата запроса: {timestamp}\n"
    f"Зал: {ctx.user_data['zone']}\n"
    f"Столик: {ctx.user_data['table']}\n"
    f"Время брони: {ctx.user_data['datetime']}\n"
    f"Гостей: {ctx.user_data['people']}\n"
    f"Предоплата: 1000 сом"
)
await context.bot.send_message(
    chat_id=os.getenv(""),
    text=group_msg,
    parse_mode="HTML"
)


# AI-меню
async def ai_allergy(update, ctx):
    uid=update.effective_user.id
    allergy=[i.strip().lower() for i in update.message.text.split(",")]
    users[uid]["allergy"]=allergy
    allowed=[d["name"] for d in dishes if not(set(d["ingredients"])&set(allergy))]
    await update.message.reply_text(texts[users[uid]["lang"]]["ai_menu"] + "\n".join(allowed))
    return ConversationHandler.END

# Музыка
async def music_name(update, ctx):
    uid=update.effective_user.id
    ctx.user_data["track"]=update.message.text
    await update.message.reply_text(t(uid,"music_confirm").format(track=ctx.user_data["track"]))
    return MUSIC_CONFIRM

async def music_confirm(update, ctx):
    uid=update.effective_user.id; txt=update.message.text.lower()
    if txt in ["да","yes"]:
        track=ctx.user_data["track"]
        dj=dj_schedule[datetime.now().weekday()]
        await update.message.reply_text(t(uid,"thank_you"))
        await ctx.bot.send_message(
            chat_id=os.getenv("GROUP_CHAT_ID"),
            text=f"Заказ музыки: {track}, DJ: {dj}"
        )
    else:
        await update.message.reply_text(t(uid,"cancel"))
    return ConversationHandler.END

# Отзыв
async def review_choice(update, ctx):
    ctx.user_data["anon"] = (update.message.text == "Анонимно")
    await update.message.reply_text("Напишите отзыв:")
    return REVIEW_TEXT

async def review_text(update, ctx):
    uid=update.effective_user.id
    text=update.message.text
    name = users[uid]["name"] if not ctx.user_data.get("anon") else "Аноним"
    await update.message.reply_text(t(uid,"review_thanks"))
    await ctx.bot.send_message(
        chat_id=os.getenv("-1002705399393"),
        text=f"Новый отзыв от {name}:\n{text}"
    )
    return ConversationHandler.END

# Отмена
async def cancel(update, ctx):
    uid=update.effective_user.id
    await update.message.reply_text(t(uid,"cancel"))
    return ConversationHandler.END

def main():
    token=os.getenv("8003288203:AAHWtHosG1kKRf0yd123i4yVn0Vx7GMakBA")
    app = ApplicationBuilder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG:    [MessageHandler(filters.TEXT, set_lang)],
            ASK_NAME:[MessageHandler(filters.TEXT, set_name)],
            MENU:    [MessageHandler(filters.TEXT, menu_choice)],
            BOOK_DATE:  [MessageHandler(filters.TEXT, book_date)],
            BOOK_PEOPLE:[MessageHandler(filters.TEXT, book_people)],
            BOOK_ZONE:  [MessageHandler(filters.TEXT, book_zone)],
            BOOK_TABLE: [CallbackQueryHandler(book_table_cb)],
            AI_ALLERGY:[MessageHandler(filters.TEXT, ai_allergy)],
            MUSIC_NAME:[MessageHandler(filters.TEXT, music_name)],
            MUSIC_CONFIRM:[MessageHandler(filters.TEXT, music_confirm)],
            REVIEW_CHOICE:[MessageHandler(filters.TEXT, review_choice)],
            REVIEW_TEXT:[MessageHandler(filters.TEXT, review_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
