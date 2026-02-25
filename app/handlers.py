from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart, Command
from aiogram.dispatcher.filters.state import State, StatesGroup
import app.keyboards as kb
from app.ai_teacher import generate_lesson, check_answer
from app.database import (
    get_or_create_user, update_streak, add_xp, save_answer, 
    complete_lesson, get_user_stats, init_user_topics,
    get_current_topic, get_completed_topics, get_all_topics,
    start_repeating_topic, get_next_pending_topic, 
    get_repeating_topics, calculate_progress_percentage, complete_topic
)

# Состояния для хранения контекста урока
class LessonStates(StatesGroup):
    waiting_for_answer = State()
    current_topic_id = State()
    current_topic_name = State()
    current_topic_level = State()

# ==================== ОБРАБОТЧИКИ КОМАНД ====================

async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    # Сохраняем пользователя в базу
    user = get_or_create_user(
        message.from_user.id,
        message.from_user.first_name,
        message.from_user.username
    )
    
    # Инициализируем темы для нового пользователя
    init_user_topics(message.from_user.id)
    
    # Обновляем серию
    update_streak(message.from_user.id)
    
    # Получаем обновлённые данные
    stats = get_user_stats(message.from_user.id)
    user = stats['user']
    
    # Получаем текущую тему
    current_topic = get_current_topic(message.from_user.id)
    current_topic_name = current_topic['topic_name'] if current_topic else "Не выбрана"
    
    # Прогресс
    progress = calculate_progress_percentage(message.from_user.id)
    
    welcome_text = (
        "👋 <b>Welcome to NeuroEnglish!</b>\n\n"
        "Привет! Я твой личный AI-учитель английского.\n"
        "У нас есть <b>30 тем</b> — от новичка до разговорного уровня.\n\n"
        f"📊 <b>Твой прогресс:</b> {progress}%\n"
        f"🔥 Серия: {user['current_streak']} дней\n"
        f"✨ Всего XP: {user['total_xp']}\n"
        f"📚 Текущая тема: <b>{current_topic_name}</b>\n\n"
        "Выбери действие:"
    )
    
    await message.answer(welcome_text, reply_markup=kb.main_menu, parse_mode="HTML")

async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = (
        "🔍 <b>Помощь</b>\n\n"
        "/start - Главное меню\n"
        "📚 Новый урок - следующий урок по программе\n"
        "📊 Мой прогресс - статистика\n"
        "🔄 Повторить тему - выбрать тему для повторения\n"
        "❓ Помощь - эта справка\n\n"
        "Всего 30 тем. После каждой темы ты получаешь XP и продвигаешься дальше!"
    )
    await message.answer(help_text, parse_mode="HTML", reply_markup=kb.main_menu)

# ==================== ОБРАБОТЧИКИ КНОПОК ====================

async def new_lesson(message: types.Message, state: FSMContext = None):
    """Начать новый урок"""
    if state:
        await state.finish()
    
    # Получаем текущую тему для пользователя
    current_topic = get_current_topic(message.from_user.id)
    
    if not current_topic:
        # Если нет текущей темы, берём следующую
        next_topic = get_next_pending_topic(message.from_user.id)
        if next_topic:
            current_topic = next_topic
        else:
            # Если все темы пройдены
            await message.answer(
                "🎉 <b>Поздравляю!</b> Ты прошёл все 30 тем!\n\n"
                "Теперь ты можешь повторять любые темы или просто практиковаться в разговоре.\n"
                "Нажми '🔄 Повторить тему', чтобы выбрать что-то для повторения.",
                reply_markup=kb.main_menu,
                parse_mode="HTML"
            )
            return
    
    await message.answer(
        f"⏳ Генерирую урок на тему <b>{current_topic['topic_name']}</b>... Подожди секунду...", 
        parse_mode="HTML"
    )
    
    # Генерируем урок через DeepSeek
    lesson = await generate_lesson(level=current_topic['topic_level'], topic=current_topic['topic_name'])
    
    # Отправляем урок
    await message.answer(lesson, parse_mode="HTML")
    
    # Сохраняем тему урока в состояние
    await LessonStates.waiting_for_answer.set()
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
    await state.update_data(
        current_topic_id=current_topic['id'],
        current_topic_name=current_topic['topic_name'],
        current_topic_level=current_topic['topic_level']
    )

async def show_progress(message: types.Message):
    """Показать прогресс пользователя"""
    stats = get_user_stats(message.from_user.id)
    user = stats['user']
    
    # Получаем все темы
    all_topics = get_all_topics(message.from_user.id)
    completed_topics = get_completed_topics(message.from_user.id)
    current_topic = get_current_topic(message.from_user.id)
    
    # Прогресс
    progress = calculate_progress_percentage(message.from_user.id)
    
    # Определяем уровень по XP
    if user['total_xp'] < 500:
        level = "🔰 Новичок"
    elif user['total_xp'] < 1500:
        level = "📘 Исследователь"
    elif user['total_xp'] < 3000:
        level = "📗 Путешественник"
    elif user['total_xp'] < 5000:
        level = "📕 Граммар-ниндзя"
    else:
        level = "🏆 Мастер разговора"
    
    # Процент правильных ответов
    if stats['total_answers'] > 0:
        accuracy = (stats['correct_answers'] / stats['total_answers']) * 100
    else:
        accuracy = 0
    
    # Статистика по темам
    completed_count = len(completed_topics)
    total_count = len(all_topics) if all_topics else 30
    
    progress_text = (
        "📊 <b>Твой прогресс</b>\n\n"
        f"🔥 Серия: {user['current_streak']} дней "
        f"(рекорд: {user['best_streak']})\n"
        f"✨ Всего XP: {user['total_xp']}\n"
        f"✅ Точность: {accuracy:.1f}%\n"
        f"🎯 Уровень: {level}\n\n"
        f"📚 <b>Темы:</b> {completed_count}/{total_count} ({progress}%)\n"
    )
    
    if current_topic:
        progress_text += f"📖 Текущая тема: <b>{current_topic['topic_name']}</b>\n"
    
    progress_text += "\nНажми '📚 Новый урок', чтобы продолжить!"
    
    await message.answer(progress_text, parse_mode="HTML", reply_markup=kb.main_menu)

async def repeat_topic_menu(message: types.Message):
    """Меню выбора темы для повторения"""
    # Получаем все пройденные темы
    completed = get_completed_topics(message.from_user.id)
    repeating = get_repeating_topics(message.from_user.id)
    
    if not completed and not repeating:
        await message.answer(
            "📭 У тебя пока нет пройденных тем. Сначала пройди несколько уроков!",
            reply_markup=kb.main_menu
        )
        return
    
    # Создаём клавиатуру с темами для повторения
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    
    topics_keyboard = []
    
    # Добавляем пройденные темы
    for topic in completed[:10]:
        short_name = topic['topic_name'][:30]
        topics_keyboard.append([KeyboardButton(text=f"🔄 {short_name}")])
    
    # Добавляем темы на повторении
    for topic in repeating:
        short_name = topic['topic_name'][:30]
        topics_keyboard.append([KeyboardButton(text=f"🔁 {short_name} (повтор)")])
    
    topics_keyboard.append([KeyboardButton(text="⬅️ В меню")])
    
    repeat_keyboard = ReplyKeyboardMarkup(
        keyboard=topics_keyboard,
        resize_keyboard=True
    )
    
    await message.answer(
        "📚 <b>Выбери тему для повторения:</b>\n\n"
        "🔄 — пройденные темы\n"
        "🔁 — темы, которые уже на повторении\n\n"
        "Просто нажми на нужную тему:",
        reply_markup=repeat_keyboard,
        parse_mode="HTML"
    )

async def help_button(message: types.Message):
    """Кнопка помощи"""
    await cmd_help(message)

# ==================== ОБРАБОТЧИКИ СОСТОЯНИЙ ====================

async def cancel_lesson(message: types.Message, state: FSMContext):
    """Выход из урока в главное меню"""
    await state.finish()
    await message.answer(
        "👋 Возвращаюсь в главное меню. Хочешь продолжить позже — нажимай 'Новый урок'!",
        reply_markup=kb.main_menu,
        parse_mode="HTML"
    )

async def new_lesson_during_lesson(message: types.Message, state: FSMContext):
    """Начать новый урок во время текущего"""
    await state.finish()
    await new_lesson(message)

async def handle_answer(message: types.Message, state: FSMContext):
    """Обработка ответа на задание"""
    user_answer = message.text
    data = await state.get_data()
    topic_id = data.get('current_topic_id')
    topic_name = data.get('current_topic_name', 'unknown')
    
    await message.answer("⏳ Проверяю ответ...")
    
    # Проверяем ответ через DeepSeek
    feedback = await check_answer(
        question=f"Задание по теме '{topic_name}'",
        user_answer=user_answer
    )
    
    # Простая проверка для начисления XP
    correct = len(user_answer.split()) >= 2
    
    # Сохраняем в базу
    save_answer(
        message.from_user.id,
        topic_name,
        f"Урок по теме {topic_name}",
        user_answer,
        correct
    )
    
    if correct:
        add_xp(message.from_user.id, 10)
        
        # Отмечаем тему как пройденную
        complete_topic(message.from_user.id, topic_id)
        
        # Получаем следующую тему
        next_topic = get_next_pending_topic(message.from_user.id)
        progress = calculate_progress_percentage(message.from_user.id)
        
        feedback += f"\n\n✅ <b>+10 XP!</b>"
        feedback += f"\n📊 <b>Прогресс: {progress}%</b>"
        
        if next_topic:
            feedback += f"\n📚 Следующая тема: <b>{next_topic['topic_name']}</b>"
        else:
            feedback += "\n🎉 Ты прошёл все темы! Можешь повторить что угодно."
    
    # Обновляем серию
    update_streak(message.from_user.id)
    
    await message.answer(feedback, parse_mode="HTML", reply_markup=kb.lesson_keyboard)
    await state.finish()

async def start_repeat_lesson(message: types.Message, state: FSMContext):
    """Начать урок повторения по выбранной теме"""
    # Очищаем текст от эмодзи и пометок
    topic_text = message.text.replace("🔄 ", "").replace("🔁 ", "").replace(" (повтор)", "")
    
    # Ищем тему в базе
    topics = get_all_topics(message.from_user.id)
    selected_topic = None
    
    for topic in topics:
        if topic['topic_name'] in topic_text or topic_text in topic['topic_name']:
            selected_topic = topic
            break
    
    if selected_topic:
        # Начинаем повторение
        start_repeating_topic(message.from_user.id, selected_topic['id'])
        
        await message.answer(
            f"⏳ Генерирую урок для повторения темы <b>{selected_topic['topic_name']}</b>...", 
            parse_mode="HTML"
        )
        
        # Генерируем урок
        lesson = await generate_lesson(level=selected_topic['topic_level'], topic=selected_topic['topic_name'])
        
        await message.answer(lesson, parse_mode="HTML")
        
        await LessonStates.waiting_for_answer.set()
        state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
        await state.update_data(
            current_topic_id=selected_topic['id'],
            current_topic_name=selected_topic['topic_name'],
            current_topic_level=selected_topic['topic_level']
        )
    else:
        await message.answer(
            "❌ Тема не найдена. Попробуй ещё раз выбрать из списка.",
            reply_markup=kb.main_menu
        )

async def handle_unknown(message: types.Message):
    """Обработка любых других сообщений"""
    await message.answer(
        "Я не понял команду. Используй кнопки или напиши /start",
        reply_markup=kb.main_menu
    )

# ==================== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ====================

def register_handlers(dp: Dispatcher):
    """Регистрирует все обработчики в диспетчере"""
    # Команды
    dp.register_message_handler(cmd_start, commands=['start'])
    dp.register_message_handler(cmd_help, commands=['help'])
    
    # Кнопки меню
    dp.register_message_handler(new_lesson, lambda message: message.text == "📚 Новый урок")
    dp.register_message_handler(show_progress, lambda message: message.text == "📊 Мой прогресс")
    dp.register_message_handler(repeat_topic_menu, lambda message: message.text == "🔄 Повторить тему")
    dp.register_message_handler(help_button, lambda message: message.text == "❓ Помощь")
    
    # Обработчики состояний (важен порядок!)
    dp.register_message_handler(cancel_lesson, state=LessonStates.waiting_for_answer, text="⬅️ В меню")
    dp.register_message_handler(new_lesson_during_lesson, state=LessonStates.waiting_for_answer, text="📚 Новый урок")
    dp.register_message_handler(handle_answer, state=LessonStates.waiting_for_answer)
    
    # Обработчик выбора темы для повторения
    dp.register_message_handler(start_repeat_lesson, lambda message: message.text.startswith("🔄") or message.text.startswith("🔁"))
    
    # Обработчик всего остального (должен быть последним)
    dp.register_message_handler(handle_unknown)