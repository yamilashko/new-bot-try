from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import pandas as pd
import os
from dotenv import load_dotenv

# --- Настройки ---
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Базы данных (в памяти)
reviews_db = pd.DataFrame(columns=["user_id", "user_name", "rating", "text"])
users_db = pd.DataFrame(columns=["user_id", "referral_code", "bonus_points"])

# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    args = context.args

    if args and args[0].startswith("ref"):
        referrer_id = int(args[0][3:])
        users_db.loc[len(users_db)] = [user.id, f"ref{referrer_id}", 0]
        await update.message.reply_text("🎉 Вы зашли по ссылке друга! Он получит бонус.")

    keyboard = [
        [InlineKeyboardButton("🎮 Викторина", callback_data="quiz")],
        [InlineKeyboardButton("📝 Оставить отзыв", callback_data="feedback")]
    ]
    await update.message.reply_text(
        f"Привет, {user.first_name}! Добро пожаловать в баню!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Геймификация ---
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("60°C", callback_data="quiz_60")],
        [InlineKeyboardButton("80°C", callback_data="quiz_80")],
        [InlineKeyboardButton("100°C", callback_data="quiz_100")]
    ]
    await query.edit_message_text(
        "🎉 Угадайте температуру в парной и получите скидку:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    answer = query.data.split("_")[1]

    if answer == "80":
        await query.edit_message_text("✅ Верно! Ваш промокод: BANIA15 (скидка 15%)")
    else:
        await query.edit_message_text("❌ Не угадали! Вот промокод: BANIA5")

# --- Сбор отзывов ---
async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(star, callback_data=f"rate_{i+1}")] 
        for i, star in enumerate(["⭐️", "⭐️⭐️", "⭐️⭐️⭐️", "⭐️⭐️⭐️⭐️", "⭐️⭐️⭐️⭐️⭐️"])
    ]
    await query.edit_message_text("Оцените ваш визит:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rating = int(query.data.split("_")[1])
    user = query.from_user

    global reviews_db
    reviews_db.loc[len(reviews_db)] = [user.id, user.first_name, rating, ""]
    
    if rating >= 4:
        await query.edit_message_text("Напишите отзыв текстом (и получите подарок!)")
        context.user_data["waiting_feedback"] = True
    else:
        await query.edit_message_text("Что пошло не так? Опишите проблему:")
        context.user_data["waiting_feedback"] = True

async def save_text_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_feedback"):
        text = update.message.text
        user = update.message.from_user
        
        reviews_db.loc[reviews_db["user_id"] == user.id, "text"] = text
        reviews_db.to_excel("reviews.xlsx")
        
        await update.message.reply_text("Спасибо! Ваш отзыв сохранён.")
        context.user_data["waiting_feedback"] = False

# --- Запуск ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(quiz, pattern="^quiz$"))
    app.add_handler(CallbackQueryHandler(handle_quiz_answer, pattern="^quiz_"))
    app.add_handler(CallbackQueryHandler(feedback, pattern="^feedback$"))
    app.add_handler(CallbackQueryHandler(handle_rating, pattern="^rate_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_text_review))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
