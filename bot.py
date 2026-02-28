import os
import asyncio
import logging
import uvicorn
from starlette.applications import Starlette
from starlette.responses import Response, PlainTextResponse
from starlette.routing import Route
from starlette.requests import Request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, ContextTypes, MessageHandler, filters, CommandHandler

# Подключаем только базу уроков (ai_teacher больше не нужен)
from lessons_db import get_lesson, get_next_lesson, get_lessons_count
from app.database import (
    get_or_create_user, update_streak, add_xp, save_answer,
    complete_lesson, get_user_stats
)

# --- Настройки ---
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
RENDER_URL = os.environ["RENDER_EXTERNAL_URL"]
PORT = int(os.getenv("PORT", 8000))

# Логирование
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Клавиатуры
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📚 Следующий урок"), KeyboardButton("📊 Мой прогресс")],
        [KeyboardButton("🎯 Выбрать уровень"), KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_lesson_keyboard():
    keyboard = [
        [KeyboardButton("📚 Следующий урок")],
        [KeyboardButton("⬅️ В главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_level_keyboard():
    levels = ["A0-A1", "A1-A2", "A2-B1", "B1-B2", "B2-C1"]
    keyboard = [[KeyboardButton(level)] for level in levels]
    keyboard.append([KeyboardButton("⬅️ В главное меню")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- ОБРАБОТЧИКИ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    
    # Сохраняем пользователя в базу
    get_or_create_user(user.id, user.first_name, user.username)
    
    total_lessons = get_lessons_count()
    
    welcome_text = (
        "👋 <b>Welcome to NeuroEnglish!</b>\n\n"
        "Привет! Это твой личный AI-учитель английского.\n"
        "У нас есть <b>1050 готовых уроков</b> — от A0 до C1.\n\n"
        "📚 <b>Все уроки созданы по методике Александра Бебриса</b>\n\n"
        "Нажми <b>«Следующий урок»</b>, чтобы начать!"
    )
    
    await update.message.reply_text(welcome_text, parse_mode="HTML", reply_markup=get_main_keyboard())

async def next_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Получаем текущий урок пользователя
    current_lesson_id = context.user_data.get('current_lesson_id', 1)
    
    # Получаем урок из базы
    lesson = get_lesson(current_lesson_id)
    
    if not lesson:
        # Если уроков больше нет
        total = get_lessons_count()
        if current_lesson_id > total:
            await update.message.reply_text(
                "🎉 Поздравляю! Ты прошел все 1050 уроков!\n"
                "Можешь повторить любой уровень через меню «Выбрать уровень».",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка загрузки урока. Попробуй позже.",
                reply_markup=get_main_keyboard()
            )
        return
    
    # Формируем сообщение с уроком
    lesson_text = (
        f"📚 <b>Урок {lesson['id']}: {lesson['topic']}</b>\n"
        f"Уровень: {lesson['level']}\n\n"
        f"{lesson['theory']}\n\n"
        f"{lesson['examples']}\n\n"
        f"{lesson['exercise']}"
    )
    
    await update.message.reply_text(lesson_text, parse_mode="HTML", reply_markup=get_lesson_keyboard())
    
    # Сохраняем состояние
    context.user_data['current_lesson_id'] = current_lesson_id
    context.user_data['waiting_for_answer'] = True
    context.user_data['current_lesson'] = lesson

async def select_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор уровня для повторения"""
    await update.message.reply_text(
        "🎯 Выбери уровень:",
        reply_markup=get_level_keyboard()
    )

async def handle_level_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора уровня"""
    level = update.message.text
    
    # Здесь можно найти первый урок выбранного уровня
    # (нужно добавить функцию в lessons_db)
    
    await update.message.reply_text(
        f"Ты выбрал уровень {level}. Нажми «Следующий урок», чтобы начать.",
        reply_markup=get_main_keyboard()
    )

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_answer = update.message.text
    
    # Проверяем, ждем ли мы ответ
    if not context.user_data.get('waiting_for_answer'):
        await update.message.reply_text(
            "Сначала начни урок командой /start или нажми «Следующий урок»",
            reply_markup=get_main_keyboard()
        )
        return
    
    lesson = context.user_data.get('current_lesson')
    if not lesson:
        await update.message.reply_text(
            "Ошибка: урок не найден",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Простая проверка (можно усложнить)
    add_xp(user_id, 10)
    save_answer(user_id, f"Урок {lesson['id']}", "Задание", user_answer, True)
    
    # Переходим к следующему уроку
    next_id = lesson['id'] + 1
    context.user_data['current_lesson_id'] = next_id
    context.user_data['waiting_for_answer'] = False
    
    await update.message.reply_text(
        f"✅ <b>Отлично! +10 XP</b>\n\n"
        f"Твой ответ принят. Можешь переходить к следующему уроку.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    user = stats['user']
    
    current = context.user_data.get('current_lesson_id', 1)
    total = get_lessons_count()
    
    progress_text = (
        "📊 <b>Твой прогресс</b>\n\n"
        f"🔥 Серия: {user['current_streak']} дней\n"
        f"✨ Всего XP: {user['total_xp']}\n"
        f"✅ Правильных ответов: {stats['correct_answers']}\n"
        f"📚 Всего ответов: {stats['total_answers']}\n\n"
        f"📈 Прогресс по курсу: {current}/{total} уроков ({current/total*100:.1f}%)"
    )
    
    await update.message.reply_text(progress_text, parse_mode="HTML", reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🔍 <b>Помощь</b>\n\n"
        "📚 <b>Следующий урок</b> — начать новый урок\n"
        "🎯 <b>Выбрать уровень</b> — перейти к конкретному уровню\n"
        "📊 <b>Мой прогресс</b> — статистика\n"
        "❓ <b>Помощь</b> — эта справка\n\n"
        f"Всего {get_lessons_count()} уроков, разбитых по уровням от A0 до C1.\n"
        "В каждом уроке: теория, примеры и задания на перевод.\n\n"
        "Методика Александра Бебриса: последовательное изучение с наслоением материала ."
    )
    
    await update.message.reply_text(help_text, parse_mode="HTML", reply_markup=get_main_keyboard())

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['waiting_for_answer'] = False
    await update.message.reply_text(
        "👋 Возвращаюсь в главное меню",
        reply_markup=get_main_keyboard()
    )

# --- ОСНОВНАЯ ФУНКЦИЯ ---
async def main():
    bot_app = Application.builder().token(TOKEN).updater(None).build()
    
    # Добавляем обработчики
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.Text("📚 Следующий урок"), next_lesson))
    bot_app.add_handler(MessageHandler(filters.Text("🎯 Выбрать уровень"), select_level))
    bot_app.add_handler(MessageHandler(filters.Regex('^(A0-A1|A1-A2|A2-B1|B1-B2|B2-C1)$'), handle_level_choice))
    bot_app.add_handler(MessageHandler(filters.Text("📊 Мой прогресс"), progress))
    bot_app.add_handler(MessageHandler(filters.Text("❓ Помощь"), help_command))
    bot_app.add_handler(MessageHandler(filters.Text("⬅️ В главное меню"), back_to_menu))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    
    # Устанавливаем вебхук
    webhook_url = f"{RENDER_URL}/webhook"
    await bot_app.bot.set_webhook(url=webhook_url, allowed_updates=Update.ALL_TYPES)
    logger.info(f"Webhook set to {webhook_url}")
    
    # Starlette приложение
    async def webhook(request: Request) -> Response:
        try:
            data = await request.json()
            update = Update.de_json(data, bot_app.bot)
            await bot_app.process_update(update)
            return Response()
        except Exception as e:
            logger.exception("Error processing webhook")
            return Response(status_code=500)
    
    async def health_check(request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")
    
    starlette_app = Starlette(routes=[
        Route("/webhook", webhook, methods=["POST"]),
        Route("/health", health_check, methods=["GET"]),
        Route("/healthcheck", health_check, methods=["GET"]),
    ])
    
    server = uvicorn.Server(
        uvicorn.Config(
            app=starlette_app,
            host="0.0.0.0",
            port=PORT,
            log_level="info"
        )
    )
    
    logger.info(f"Server starting on port {PORT}")
    async with bot_app:
        await bot_app.start()
        await server.serve()
        await bot_app.stop()

if __name__ == "__main__":
    asyncio.run(main())