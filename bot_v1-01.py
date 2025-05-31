import os
import logging
from datetime import datetime, time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file!")

# Словарь для хранения привычек пользователей
user_habits = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить привычку", callback_data='add_habit')],
        [InlineKeyboardButton("📋 Мои привычки", callback_data='list_habits')],
        [InlineKeyboardButton("❌ Удалить привычку", callback_data='delete_habit')],
        [InlineKeyboardButton("📊 Статистика", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Привет, {update.effective_user.first_name}!\n\n"
        "Я помогу тебе отслеживать твои привычки.\n\n"
        "Выбери действие из меню ниже:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'add_habit':
        await query.message.reply_text(
            "Отправь мне название новой привычки, которую хочешь отслеживать."
        )
        context.user_data['state'] = 'adding_habit'
    
    elif query.data == 'list_habits':
        user_id = query.from_user.id
        if user_id not in user_habits or not user_habits[user_id]:
            await query.message.reply_text("У тебя пока нет добавленных привычек.")
        else:
            habits_text = "Твои привычки:\n\n"
            for habit in user_habits[user_id]:
                habits_text += f"• {habit['name']}\n"
            await query.message.reply_text(habits_text)
    
    elif query.data == 'delete_habit':
        user_id = query.from_user.id
        if user_id not in user_habits or not user_habits[user_id]:
            await query.message.reply_text("У тебя пока нет добавленных привычек.")
        else:
            keyboard = []
            for i, habit in enumerate(user_habits[user_id]):
                keyboard.append([InlineKeyboardButton(f"❌ {habit['name']}", callback_data=f'del_{i}')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "Выбери привычку, которую хочешь удалить:",
                reply_markup=reply_markup
            )
    
    elif query.data.startswith('del_'):
        user_id = query.from_user.id
        habit_index = int(query.data.split('_')[1])
        if user_id in user_habits and 0 <= habit_index < len(user_habits[user_id]):
            deleted_habit = user_habits[user_id].pop(habit_index)
            await query.message.reply_text(
                f"Привычка '{deleted_habit['name']}' успешно удалена!"
            )
    
    elif query.data == 'stats':
        user_id = query.from_user.id
        if user_id not in user_habits or not user_habits[user_id]:
            await query.message.reply_text("Пока нет данных для статистики.")
        else:
            stats_text = "Статистика по привычкам:\n\n"
            for habit in user_habits[user_id]:
                stats_text += f"📊 {habit['name']}\n"
                stats_text += f"Серия: {habit.get('streak', 0)} дней\n\n"
            await query.message.reply_text(stats_text)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    if context.user_data.get('state') == 'adding_habit':
        habit_name = update.message.text
        user_id = update.effective_user.id
        
        if user_id not in user_habits:
            user_habits[user_id] = []
        
        new_habit = {
            'name': habit_name,
            'created_at': datetime.now(),
            'streak': 0,
            'last_checked': None
        }
        
        user_habits[user_id].append(new_habit)
        context.user_data['state'] = None
        
        await update.message.reply_text(
            f"Привычка '{habit_name}' добавлена!"
        )
    else:
        await update.message.reply_text(
            "Для начала работы с ботом отправьте команду /start"
        )

def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 