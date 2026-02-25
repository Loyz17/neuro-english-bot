import os
from aiogram import Bot, Dispatcher, executor
from dotenv import load_dotenv
from app.database import init_db
from app.handlers import dp

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
    
    # Запуск бота (aiogram 2.x)
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )