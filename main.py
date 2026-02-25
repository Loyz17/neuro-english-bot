import os
import asyncio
from threading import Thread
from aiogram import Bot, Dispatcher, executor
from dotenv import load_dotenv
from app.database import init_db
from app.handlers import register_handlers

# Запускаем health check сервер в отдельном потоке, чтобы не блокировать бота
def run_health_check():
    from aiohttp import web
    import asyncio
    
    async def health_check(request):
        return web.Response(text="OK")
    
    async def run_server():
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        app.router.add_get('/healthcheck', health_check)
        
        port = int(os.environ.get('PORT', 10000))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        print(f"✅ Health check server started on port {port}")
        await site.wait_closed()
    
    # Создаем новый event loop для потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_server())

async def on_startup(dp):
    """Действия при запуске бота"""
    init_db()
    print('✅ Bot starting up...')

async def on_shutdown(dp):
    """Действия при остановке бота"""
    print('❌ Bot is shutting down...')

if __name__ == '__main__':
    load_dotenv()
    bot = Bot(token=os.getenv('TG_TOKEN'))
    
    # Запускаем health check сервер в отдельном потоке
    health_thread = Thread(target=run_health_check, daemon=True)
    health_thread.start()
    print("✅ Health check thread started")
    
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