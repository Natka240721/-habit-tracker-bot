import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Импортируем все функции из основного файла бота
from bot import start, button_handler, message_handler, TOKEN

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем Flask приложение
app = Flask(__name__)

# Создаем приложение бота
application = Application.builder().token(TOKEN).build()

# Добавляем обработчики
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

@app.route('/' + TOKEN, methods=['POST'])
async def webhook():
    """Обработчик веб-хуков от Telegram"""
    try:
        update = Update.de_json(request.get_json(), application.bot)
        await application.process_update(update)
        return 'ok'
    except Exception as e:
        logger.error(f"Ошибка при обработке веб-хука: {e}")
        return 'error'

@app.route('/')
def index():
    """Страница для проверки работоспособности"""
    return 'Бот работает!'

if __name__ == '__main__':
    # Запускаем Flask приложение
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 