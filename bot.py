import os
import asyncio
import logging
import json
import uvicorn
from starlette.applications import Starlette
from starlette.responses import Response, PlainTextResponse
from starlette.routing import Route
from starlette.requests import Request
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters, CommandHandler

# --- Твои старые функции (подключаем обратно) ---
from app.ai_teacher import generate_lesson, check_answer
from app.database import (
    get_or_create_user, update_streak, add_xp, save_answer,
    complete_lesson, get_user_stats, init_user_topics,
    get_current_topic, get_completed_topics, get_all_topics,
    start_repeating_topic, get_next_pending_topic,
    get_repeating_topics, calculate_progress_percentage, complete_topic
)

# --- Настройки ---
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
RENDER_URL = os.environ["RENDER_EXTERNAL_URL"]
PORT = int(os.getenv("PORT", 8000))

# Логирование
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# === ТВОИ ОБРАБОТЧИКИ (из старых файлов, адаптированные для нового бота) ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    
    # Сохраняем пользователя в базу
    db_user = get_or_create_user(user.id, user.first_name, user.username)
    
    # Инициализируем темы для нового пользователя
    init_user_topics(user.id)
    
    # Обновляем серию
    update_streak(user.id)
    
    # Получаем текущую тему
    current_topic = get_current_topic(user.id)
    current_topic_name = current_topic['topic_name'] if current_topic else "Не выбрана"
    
    # Прогресс
    progress = calculate_progress_percentage(user.id)
    
    welcome_text = (
        "👋 <b>Welcome to NeuroEnglish!</b>\n\n"
        "Привет! Я твой личный AI-учитель английского.\n"
        "У нас есть <b>30 тем</b> — от новичка до разговорного уровня.\n\n"
        f"📊 <b>Твой прогресс:</b> {progress}%\n"
        f"🔥 Серия: {db_user['current_streak']} дней\n"
        f"✨ Всего XP: {db_user['total_xp']}\n"
        f"📚 Текущая тема: <b>{current_topic_name}</b>\n\n"
        "Выбери действие: /lesson - новый урок, /progress - статистика"
    )
    
    await update.message.reply_text(welcome_text, parse_mode="HTML")

async def lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать новый урок"""
    user_id = update.effective_user.id
    
    # Получаем текущую тему
    current_topic = get_current_topic(user_id)
    
    if not current_topic:
        next_topic = get_next_pending_topic(user_id)
        if next_topic:
            current_topic = next_topic
        else:
            await update.message.reply_text(
                "🎉 <b>Поздравляю!</b> Ты прошёл все 30 тем!",
                parse_mode="HTML"
            )
            return
    
    await update.message.reply_text(
        f"⏳ Генерирую урок на тему <b>{current_topic['topic_name']}</b>... Подожди секунду...",
        parse_mode="HTML"
    )
    
    # Генерируем урок
    lesson = await generate_lesson(level=current_topic['topic_level'], topic=current_topic['topic_name'])
    
    await update.message.reply_text(lesson, parse_mode="HTML")
    
    # Сохраняем тему в context.user_data для следующего шага
    context.user_data['current_topic_id'] = current_topic['id']
    context.user_data['current_topic_name'] = current_topic['topic_name']

async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать прогресс"""
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    user = stats['user']
    
    all_topics = get_all_topics(user_id)
    completed_topics = get_completed_topics(user_id)
    progress = calculate_progress_percentage(user_id)
    
    progress_text = (
        "📊 <b>Твой прогресс</b>\n\n"
        f"🔥 Серия: {user['current_streak']} дней\n"
        f"✨ XP: {user['total_xp']}\n"
        f"📚 Тем пройдено: {len(completed_topics)}/{len(all_topics)} ({progress}%)\n"
    )
    
    await update.message.reply_text(progress_text, parse_mode="HTML")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов на уроки"""
    user_id = update.effective_user.id
    user_answer = update.message.text
    
    # Получаем сохранённую тему из context
    topic_id = context.user_data.get('current_topic_id')
    topic_name = context.user_data.get('current_topic_name', 'unknown')
    
    if not topic_id:
        await update.message.reply_text("Сначала начни урок командой /lesson")
        return
    
    await update.message.reply_text("⏳ Проверяю ответ...")
    
    # Проверяем ответ
    feedback = await check_answer(
        question=f"Задание по теме '{topic_name}'",
        user_answer=user_answer
    )
    
    # Простая проверка для начисления XP
    correct = len(user_answer.split()) >= 2
    
    # Сохраняем в базу
    save_answer(user_id, topic_name, "Урок", user_answer, correct)
    
    if correct:
        add_xp(user_id, 10)
        complete_topic(user_id, topic_id)
        
        next_topic = get_next_pending_topic(user_id)
        progress = calculate_progress_percentage(user_id)
        
        feedback += f"\n\n✅ <b>+10 XP!</b>"
        feedback += f"\n📊 <b>Прогресс: {progress}%</b>"
        
        if next_topic:
            feedback += f"\n📚 Следующая тема: /lesson"
        else:
            feedback += "\n🎉 Все темы пройдены!"
        
        # Очищаем сохранённую тему
        del context.user_data['current_topic_id']
    else:
        # Если ответ неправильный, оставляем тему для повторной попытки
        pass
    
    update_streak(user_id)
    await update.message.reply_text(feedback, parse_mode="HTML")

# === ОСНОВНАЯ ФУНКЦИЯ ===

async def main():
    # Создаем приложение Telegram бота
    bot_app = Application.builder().token(TOKEN).updater(None).build()
    
    # Добавляем обработчики команд
    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CommandHandler("lesson", lesson_command))
    bot_app.add_handler(CommandHandler("progress", progress_command))
    
    # Обработчик текстовых сообщений (для ответов на уроки)
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Устанавливаем вебхук
    webhook_url = f"{RENDER_URL}/webhook"
    await bot_app.bot.set_webhook(url=webhook_url, allowed_updates=Update.ALL_TYPES)
    logger.info(f"Вебхук установлен на {webhook_url}")
    
    # Создаем Starlette приложение
    async def webhook(request: Request) -> Response:
        try:
            data = await request.json()
            update = Update.de_json(data, bot_app.bot)
            await bot_app.process_update(update)
            return Response()
        except Exception as e:
            logger.exception("Ошибка при обработке вебхука")
            return Response(status_code=500)
    
    async def health_check(request: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")
    
    starlette_app = Starlette(routes=[
        Route("/webhook", webhook, methods=["POST"]),
        Route("/health", health_check, methods=["GET"]),
        Route("/healthcheck", health_check, methods=["GET"]),
    ])
    
    # Запускаем сервер
    server = uvicorn.Server(
        uvicorn.Config(
            app=starlette_app,
            host="0.0.0.0",
            port=PORT,
            log_level="info"
        )
    )
    
    logger.info(f"Сервер запускается на порту {PORT}")
    async with bot_app:
        await bot_app.start()
        await server.serve()
        await bot_app.stop()

if __name__ == "__main__":
    asyncio.run(main())