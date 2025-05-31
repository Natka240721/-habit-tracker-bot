import os
import json
import logging
from datetime import datetime, time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Отключаем логи от библиотек
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file!")

# Путь к файлу с привычками
HABITS_FILE = 'data/habits.json'

# Создаем директорию data, если её нет
os.makedirs('data', exist_ok=True)

# Словарь для хранения привычек пользователей
user_habits = {}

def load_habits():
    """Загрузка привычек из файла"""
    global user_habits
    try:
        if os.path.exists(HABITS_FILE):
            with open(HABITS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Преобразуем строковые ключи обратно в int
                user_habits = {int(k): v for k, v in data.items()}
    except Exception as e:
        logger.error(f"Ошибка при загрузке привычек: {e}")
        user_habits = {}

def save_habits():
    """Сохранение привычек в файл"""
    try:
        with open(HABITS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_habits, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при сохранении привычек: {e}")

# Загружаем привычки при запуске
load_habits()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.first_name}) запустил бота командой /start")
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить привычку", callback_data='add_habit')],
        [InlineKeyboardButton("📋 Мои привычки", callback_data='list_habits')],
        [InlineKeyboardButton("❌ Удалить привычку", callback_data='delete_habit')],
        [InlineKeyboardButton("📊 Статистика", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я помогу тебе отслеживать твои привычки.\n\n"
        "Выбери действие из меню ниже:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    user = query.from_user
    logger.info(f"Пользователь {user.id} ({user.first_name}) нажал кнопку: {query.data}")
    
    await query.answer()
    await query.message.delete()
    
    if query.data == 'add_habit':
        logger.info(f"Пользователь {user.id} начал процесс добавления привычки")
        await query.message.reply_text(
            "Отправь мне название новой привычки, которую хочешь отслеживать."
        )
        context.user_data['state'] = 'adding_habit'
    
    elif query.data == 'emoji_none':
        logger.info(f"Пользователь {user.id} выбрал вариант без эмодзи")
        user_id = user.id
        habit_index = context.user_data.get('current_habit')
        
        if user_id in user_habits and habit_index is not None:
            context.user_data['state'] = 'setting_time'
            
            keyboard = [
                [
                    InlineKeyboardButton("09:00", callback_data='time_09:00'),
                    InlineKeyboardButton("12:00", callback_data='time_12:00'),
                    InlineKeyboardButton("15:00", callback_data='time_15:00')
                ],
                [
                    InlineKeyboardButton("18:00", callback_data='time_18:00'),
                    InlineKeyboardButton("21:00", callback_data='time_21:00'),
                    InlineKeyboardButton("00:00", callback_data='time_00:00')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                "Хорошо, без эмодзи!\n\n"
                "Теперь выбери время для напоминания или отправь своё в формате ЧЧ:ММ:",
                reply_markup=reply_markup
            )
    
    elif query.data.startswith('time_'):
        time_str = query.data.split('_')[1]
        logger.info(f"Пользователь {user.id} выбрал время напоминания: {time_str}")
        user_id = user.id
        habit_index = context.user_data.get('current_habit')
        
        if user_id in user_habits and habit_index is not None:
            user_habits[user_id][habit_index]['reminder_time'] = time_str
            save_habits()
            emoji = user_habits[user_id][habit_index].get('emoji', '')
            name = user_habits[user_id][habit_index]['name']
            
            await query.message.reply_text(
                f"Привычка {emoji} '{name}' успешно настроена!\n"
                f"Время напоминания: {time_str} 🎉"
            )
            
            context.user_data['state'] = None
            context.user_data['current_habit'] = None
    
    elif query.data == 'list_habits':
        logger.info(f"Пользователь {user.id} запросил список привычек")
        user_id = user.id
        if user_id not in user_habits or not user_habits[user_id]:
            await query.message.reply_text("У тебя пока нет добавленных привычек.")
        else:
            habits_text = "Твои привычки:\n\n"
            for habit in user_habits[user_id]:
                emoji = habit.get('emoji', '')
                time_str = habit.get('reminder_time', 'Не установлено')
                habits_text += f"• {emoji} {habit['name']} (напоминание: {time_str})\n"
            await query.message.reply_text(habits_text)
    
    elif query.data == 'delete_habit':
        logger.info(f"Пользователь {user.id} начал процесс удаления привычки")
        user_id = user.id
        if user_id not in user_habits or not user_habits[user_id]:
            await query.message.reply_text("У тебя пока нет добавленных привычек.")
        else:
            keyboard = []
            for i, habit in enumerate(user_habits[user_id]):
                emoji = habit.get('emoji', '')
                keyboard.append([InlineKeyboardButton(f"❌ {emoji} {habit['name']}", callback_data=f'del_{i}')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "Выбери привычку, которую хочешь удалить:",
                reply_markup=reply_markup
            )
    
    elif query.data.startswith('del_'):
        habit_index = int(query.data.split('_')[1])
        logger.info(f"Пользователь {user.id} удаляет привычку с индексом {habit_index}")
        user_id = user.id
        if user_id in user_habits and 0 <= habit_index < len(user_habits[user_id]):
            deleted_habit = user_habits[user_id].pop(habit_index)
            save_habits()
            emoji = deleted_habit.get('emoji', '')
            await query.message.reply_text(
                f"Привычка {emoji} '{deleted_habit['name']}' успешно удалена!"
            )
    
    elif query.data == 'stats':
        logger.info(f"Пользователь {user.id} запросил статистику")
        user_id = user.id
        if user_id not in user_habits or not user_habits[user_id]:
            await query.message.reply_text("Пока нет данных для статистики.")
        else:
            stats_text = "Статистика по привычкам:\n\n"
            for habit in user_habits[user_id]:
                emoji = habit.get('emoji', '')
                stats_text += f"📊 {emoji} {habit['name']}\n"
                stats_text += f"Серия: {habit.get('streak', 0)} дней\n"
                stats_text += f"Напоминание: {habit.get('reminder_time', 'Не установлено')}\n\n"
            await query.message.reply_text(stats_text)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user = update.effective_user
    current_state = context.user_data.get('state')
    logger.info(f"Пользователь {user.id} ({user.first_name}) отправил сообщение в состоянии {current_state}: {update.message.text}")
    
    if current_state == 'adding_habit':
        habit_name = update.message.text
        logger.info(f"Пользователь {user.id} добавляет привычку: {habit_name}")
        
        if user.id not in user_habits:
            user_habits[user.id] = []
        
        new_habit = {
            'name': habit_name,
            'created_at': datetime.now().isoformat(),
            'streak': 0,
            'last_checked': None
        }
        
        user_habits[user.id].append(new_habit)
        save_habits()
        context.user_data['state'] = 'choosing_emoji'
        context.user_data['current_habit'] = len(user_habits[user.id]) - 1
        
        keyboard = [[InlineKeyboardButton("❌ Без эмодзи", callback_data='emoji_none')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Привычка '{habit_name}' добавлена!\n\n"
            "Отправь мне эмодзи для своей привычки или нажми 'Без эмодзи'",
            reply_markup=reply_markup
        )
    
    elif current_state == 'choosing_emoji':
        emoji = update.message.text.strip()
        logger.info(f"Пользователь {user.id} пытается установить эмодзи: {emoji}")
        
        if len(emoji) != 1 or not any(ord(c) > 0xFFFF for c in emoji):
            logger.warning(f"Пользователь {user.id} отправил некорректный эмодзи: {emoji}")
            await update.message.reply_text(
                "Пожалуйста, отправь один эмодзи или нажми 'Без эмодзи'"
            )
            return
            
        habit_index = context.user_data.get('current_habit')
        
        if user.id in user_habits and habit_index is not None:
            user_habits[user.id][habit_index]['emoji'] = emoji
            save_habits()
            logger.info(f"Пользователь {user.id} успешно установил эмодзи {emoji}")
            context.user_data['state'] = 'setting_time'
            
            keyboard = [
                [
                    InlineKeyboardButton("09:00", callback_data='time_09:00'),
                    InlineKeyboardButton("12:00", callback_data='time_12:00'),
                    InlineKeyboardButton("15:00", callback_data='time_15:00')
                ],
                [
                    InlineKeyboardButton("18:00", callback_data='time_18:00'),
                    InlineKeyboardButton("21:00", callback_data='time_21:00'),
                    InlineKeyboardButton("00:00", callback_data='time_00:00')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"Эмодзи {emoji} выбрано!\n\n"
                "Теперь выбери время для напоминания или отправь своё в формате ЧЧ:ММ:",
                reply_markup=reply_markup
            )
    
    elif current_state == 'setting_time':
        time_str = update.message.text
        logger.info(f"Пользователь {user.id} пытается установить время: {time_str}")
        
        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
            
            habit_index = context.user_data['current_habit']
            
            if user.id in user_habits and 0 <= habit_index < len(user_habits[user.id]):
                user_habits[user.id][habit_index]['reminder_time'] = time_str
                save_habits()
                emoji = user_habits[user.id][habit_index].get('emoji', '')
                name = user_habits[user.id][habit_index]['name']
                
                logger.info(f"Пользователь {user.id} успешно установил время {time_str} для привычки {name}")
                await update.message.reply_text(
                    f"Привычка {emoji} '{name}' успешно настроена!\n"
                    f"Время напоминания: {time_str} 🎉"
                )
            
            context.user_data['state'] = None
            context.user_data['current_habit'] = None
            
        except ValueError:
            logger.warning(f"Пользователь {user.id} отправил некорректное время: {time_str}")
            await update.message.reply_text(
                "Пожалуйста, отправь время в правильном формате ЧЧ:ММ\n"
                "Например: 09:00"
            )
    else:
        logger.info(f"Пользователь {user.id} отправил сообщение вне контекста: {update.message.text}")
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
    application.run_polling(allowed_updates=Update.ALL_TYPES, poll_interval=3.0)

if __name__ == '__main__':
    main() 