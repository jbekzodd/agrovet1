"""
AgroVet AI — Telegram Bot
"""
import os
import logging
from datetime import datetime, time as dtime

import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)

import database as db
import weight as wcalc

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DIAG_ANIMAL, DIAG_SYMPTOMS = range(2)
W_ANIMAL, W_GIRTH, W_LENGTH = range(2, 5)
R_ANIMAL, R_TYPE, R_DATE = range(5, 8)

MAIN_MENU = [
    ["🩺 Diagnostika", "⚖️ Vazn hisoblash"],
    ["💉 Eslatma qo'shish", "📋 Mening eslatmalarim"],
]
ANIMAL_KEYBOARD = [["🐄 Qoramol", "🐑 Qo'y/Echki"], ["⬅️ Bekor qilish"]]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌾 *AgroVet AI* ga xush kelibsiz!\n\n"
        "Men chorva mollariingiz uchun:\n"
        "🩺 Kasallik tashxisida yordam beraman\n"
        "⚖️ Taxminiy vaznni hisoblab beraman\n"
        "💉 Emlash/muolaja sanalarini eslataman\n\n"
        "Kerakli bo'limni tanlang 👇",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bekor qilindi.",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
    )
    return ConversationHandler.END


async def diag_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hayvon turini tanlang:",
        reply_markup=ReplyKeyboardMarkup(ANIMAL_KEYBOARD, resize_keyboard=True),
    )
    return DIAG_ANIMAL


async def diag_animal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "⬅️ Bekor qilish":
        return await cancel(update, context)
    context.user_data["animal"] = update.message.text
    await update.message.reply_text(
        "Kasallik belgilarini yozing (masalan: yemamayapti, isitmasi bor, holi yo'q...):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return DIAG_SYMPTOMS


async def diag_symptoms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    animal = context.user_data.get("animal", "hayvon")
    symptoms = update.message.text
    await update.message.reply_text("⏳ Sun'iy intellekt tahlil qilmoqda...")

    prompt = (
        f"Siz tajribali va ehtiyotkor veterinarsiz. "
        f"Hayvon turi: {animal}. Belgilar: {symptoms}. "
        f"O'zbek tilida, juda tushunarli va sodda qilib javob bering:\n"
        f"1. 📌 Ehtimoliy tashxis.\n2. 💡 Birinchi yordam.\n3. 💊 Tavsiya etiladigan choralar.\n"
        f"Oxirida albatta: 'Aniq tashxis uchun veterinar shifokorga murojaat qiling' deb eslatib qo'ying."
    )

    try:
        resp = requests.post(
            GEMINI_URL,
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        text = "❌ Kechirasiz, AI tahlil qila olmadi. Birozdan so'ng qayta urinib ko'ring."

    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
    return ConversationHandler.END


async def weight_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hayvon turini tanlang:",
        reply_markup=ReplyKeyboardMarkup(ANIMAL_KEYBOARD, resize_keyboard=True),
    )
    return W_ANIMAL


async def weight_animal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "⬅️ Bekor qilish":
        return await cancel(update, context)
    context.user_data["w_animal"] = "cattle" if "Qoramol" in update.message.text else "sheep"
    await update.message.reply_text(
        "📏 Ko'krak aylanasini santimetrda kiriting (o'lchov lentasi bilan ko'krak orqasidan o'lchang):\n"
        "Masalan: 165",
        reply_markup=ReplyKeyboardRemove(),
    )
    return W_GIRTH


async def weight_girth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        girth = float(update.message.text.replace(",", "."))
        context.user_data["girth"] = girth
    except ValueError:
        await update.message.reply_text("Iltimos, faqat raqam kiriting. Masalan: 165")
        return W_GIRTH
    await update.message.reply_text(
        "📏 Endi tana uzunligini santimetrda kiriting (yelkadan dumgacha):\nMasalan: 140"
    )
    return W_LENGTH


async def weight_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        length = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Iltimos, faqat raqam kiriting. Masalan: 140")
        return W_LENGTH

    girth = context.user_data["girth"]
    animal = context.user_data["w_animal"]
    formula = wcalc.FORMULAS[animal]
    result = formula(girth, length)

    await update.message.reply_text(
        f"⚖️ Taxminiy vazn: *{result} kg*\n\n"
        f"_Bu formula asosidagi taxminiy natija (aniqlik ~90-95%). "
        f"Aniq vazn uchun tarozidan foydalaning._",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
    )
    return ConversationHandler.END


async def reminder_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hayvon nomi/turini yozing (masalan: 'Qoramol - Oqposhsha' yoki 'Qo'ylar podasi'):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return R_ANIMAL


async def reminder_animal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["r_animal"] = update.message.text
    await update.message.reply_text(
        "Eslatma turini yozing (masalan: 'Emlash', 'Parazitga qarshi dori', 'Tirnoq kesish'):"
    )
    return R_TYPE


async def reminder_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["r_type"] = update.message.text
    await update.message.reply_text(
        "Sanani kiriting (YYYY-MM-DD formatida). Masalan: 2026-08-20"
    )
    return R_DATE


async def reminder_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text.strip()
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("Noto'g'ri format. Masalan: 2026-08-20 shaklida kiriting.")
        return R_DATE

    db.add_reminder(
        chat_id=update.effective_chat.id,
        animal_name=context.user_data["r_animal"],
        reminder_type=context.user_data["r_type"],
        reminder_date=date_text,
    )
    await update.message.reply_text(
        f"✅ Eslatma saqlandi!\n📅 {date_text} kuni ertalab soat 09:00 da eslataman:\n"
        f"'{context.user_data['r_animal']}' — {context.user_data['r_type']}",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
    )
    return ConversationHandler.END


async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.get_user_reminders(update.effective_chat.id)
    if not rows:
        await update.message.reply_text("Hozircha faol eslatmalaringiz yo'q.")
        return
    text = "📋 *Sizning eslatmalaringiz:*\n\n"
    for animal, rtype, date, note in rows:
        text += f"📅 {date} — {animal} ({rtype})\n"
    await update.message.reply_text(text, parse_mode="Markdown")


async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m-%d")
    rows = db.get_reminders_for_date(today)
    for reminder_id, chat_id, animal_name, reminder_type_, note in rows:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔔 *Eslatma!*\n\n'{animal_name}' uchun bugun: *{reminder_type_}*",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Eslatma yuborishda xato (chat_id={chat_id}): {e}")
        db.mark_as_sent(reminder_id)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi! .env faylini tekshiring.")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY topilmadi! .env faylini tekshiring.")

    db.init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    diag_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🩺 Diagnostika$"), diag_start)],
        states={
            DIAG_ANIMAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, diag_animal)],
            DIAG_SYMPTOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, diag_symptoms)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    weight_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⚖️ Vazn hisoblash$"), weight_start)],
        states={
            W_ANIMAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_animal)],
            W_GIRTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_girth)],
            W_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_length)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    reminder_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💉 Eslatma qo'shish$"), reminder_start)],
        states={
            R_ANIMAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminder_animal)],
            R_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminder_type)],
            R_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminder_date)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(diag_conv)
    app.add_handler(weight_conv)
    app.add_handler(reminder_conv)
    app.add_handler(MessageHandler(filters.Regex("^📋 Mening eslatmalarim$"), list_reminders))

    app.job_queue.run_daily(check_reminders, time=dtime(hour=4, minute=0))

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
