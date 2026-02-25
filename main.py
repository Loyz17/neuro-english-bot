import os
import asyncio
from aiogram import Bot, Dispatcher, executor
from dotenv import load_dotenv
from app.database import init_db
from app.handlers import register_handlers

# Простой HTTP сервер для health check
async def run_health_check_server():
    from aiohttp import web
    
    async def handle(request):
        return web.Response(text="OK")
    
    app = web.Application()
    app.router.add_get('/', handle)
    app.router.add_get('/health', handle)
    
    port = int(os.environ.get('PORT', 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    print(f"Health check server started on port {port}")
    await site.start()

async def on_startup(dp):
    """Действия при запуске бота"""
    init_db()
    # Запускаем health check сервер
    asyncio.create_task(run_health_check_server())
    print('Bot starting up...')

async def on_shutdown(dp):
    """Действия при остановке бота"""
    print('Bot is shutting down...')

if __name__ == '__main__':
    load_dotenv()
    bot = Bot(token=os.getenv('TG_TOKEN'))
    
    # Создаём диспетчер
    dp = Dispatcher(bot)
    
    # Регистрируем все обработчики
    register_handlers(dp)
    
    # Запуск бота
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )