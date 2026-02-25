import os
from aiogram import Bot, Dispatcher, executor
from dotenv import load_dotenv
from app.database import init_db
from app.handlers import register_handlers

async def on_startup(_):
    """Действия при запуске бота"""
    init_db()
    print('Bot starting up...')

async def on_shutdown(_):
    """Действия при остановке бота"""
    print('Bot is shutting down...')

if __name__ == '__main__':
    load_dotenv()
    bot = Bot(token=os.getenv('TG_TOKEN'))
    
    # Создаём диспетчер
    dp = Dispatcher(bot)
    
    # Регистрируем все обработчики (ВАЖНО: dp создаётся здесь, а не импортируется!)
    register_handlers(dp)
    
    # Запуск бота
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )