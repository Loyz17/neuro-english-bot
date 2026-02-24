import os
import sys
import asyncio
from aiohttp import web

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from app.handlers import router
from app.database import init_db

# Указываем Python использовать правильную кодировку
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Веб-приложение для health check
async def handle_health(request):
    return web.Response(text="OK", status=200)

async def init_web_server():
    app = web.Application()
    app.router.add_get('/health', handle_health)
    return app

async def main():
    # Инициализируем базу данных
    init_db()
    
    load_dotenv()
    bot = Bot(token=os.getenv('TG_TOKEN'))
    dp = Dispatcher()
    dp.include_router(router)
    
    # Запускаем веб-сервер для health check
    web_app = await init_web_server()
    runner = web.AppRunner(web_app)
    await runner.setup()
    port = int(os.getenv('PORT', 8000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Health check server started on port {port}")
    
    # Запускаем бота (polling)
    await dp.start_polling(bot)

async def startup(dispatcher: Dispatcher):
    print('Bot starting up...')

async def shutdown(dispatcher: Dispatcher):
    print('Bot is shutting down...')

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Bot stopped by user...')