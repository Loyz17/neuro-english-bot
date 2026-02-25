import os
import asyncio
import logging
import uvicorn
from starlette.applications import Starlette
from starlette.responses import Response, PlainTextResponse
from starlette.routing import Route
from starlette.requests import Request
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

# --- Настройки ---
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
# Render сам подставит сюда URL твоего сервиса
RENDER_URL = os.environ["RENDER_EXTERNAL_URL"]
PORT = int(os.getenv("PORT", 8000))

# Логирование (чтобы видеть, что происходит)
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Функция-обработчик сообщений (заменишь своей логикой позже) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает эхом на любое текстовое сообщение."""
    user_text = update.message.text
    logger.info(f"Получено сообщение: {user_text}")
    await update.message.reply_text(f"Ты сказал: {user_text}")

# --- Основная функция ---
async def main():
    # 1. Создаем приложение Telegram бота (БЕЗ Updater, т.к. используем вебхук)
    bot_app = Application.builder().token(TOKEN).updater(None).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 2. Устанавливаем вебхук. Telegram будет отправлять обновления на этот URL.
    webhook_url = f"{RENDER_URL}/webhook"
    await bot_app.bot.set_webhook(url=webhook_url, allowed_updates=Update.ALL_TYPES)
    logger.info(f"Вебхук установлен на {webhook_url}")

    # 3. Создаем Starlette приложение для обработки запросов от Telegram
    async def webhook(request: Request) -> Response:
        """Принимает POST запросы от Telegram и передает их боту."""
        try:
            data = await request.json()
            update = Update.de_json(data, bot_app.bot)
            await bot_app.process_update(update)
            return Response()
        except Exception as e:
            logger.exception("Ошибка при обработке вебхука")
            return Response(status_code=500)

    async def health_check(request: Request) -> PlainTextResponse:
        """Обязательный endpoint для Render, чтобы сервер считался живым."""
        return PlainTextResponse("OK")

    # Маршруты Starlette
    starlette_app = Starlette(routes=[
        Route("/webhook", webhook, methods=["POST"]),
        Route("/health", health_check, methods=["GET"]),
        Route("/healthcheck", health_check, methods=["GET"]), # На всякий случай
    ])

    # 4. Запускаем ASGI-сервер, который будет слушать порт и ждать запросы
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
        await server.serve()  # Блокируем тут, ждем запросы
        await bot_app.stop()

if __name__ == "__main__":
    asyncio.run(main())