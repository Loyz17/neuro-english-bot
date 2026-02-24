from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Новый урок"), KeyboardButton(text="📊 Мой прогресс")],
        [KeyboardButton(text="🔄 Повторить тему"), KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери действие..."
)

# Клавиатура для урока
lesson_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Новый урок")],
        [KeyboardButton(text="🔄 Повторить тему")],
        [KeyboardButton(text="⬅️ В меню")]
    ],
    resize_keyboard=True
)