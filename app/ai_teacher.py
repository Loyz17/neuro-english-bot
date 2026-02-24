import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Настройка клиента DeepSeek
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# Персональная инструкция от ученика (твой оригинальный запрос)
TEACHER_INSTRUCTION = """
учи меня английскийскому языку, начинай, любыми методами как хочешь но так чтобы максимально быстро хотя бы за год я мог спокойно общаться. 
если я делаю много ошибок в чем то не первый раз делай новые задания с акцентом на них чтобы они прорабатывались иногда для запоминания.
в каждом новом задании пиши процент до сотых и сколько дней мне осталось до идеального владения языком.
"""

async def generate_lesson(level="beginner", topic="to be"):
    """Генерирует урок по запросу"""
    
    prompt = f"""
{TEACHER_INSTRUCTION}

Создай короткий урок для уровня {level} на тему "{topic}".

Структура урока:
1. Короткое объяснение правила (2-3 предложения)
2. Таблица или примеры (3-4 примера)
3. Задание для ученика (перевести 2-3 предложения)

Важно: в конце урока обязательно напиши процент прогресса (например "Прогресс: 5.25%") 
и сколько дней осталось до цели (например "До свободного общения: 350 дней").

Используй эмодзи для оформления. Ответ дай на русском языке.
Форматируй текст с HTML-тегами для Telegram. Разрешены только: <b>, <i>, <u>, <s>, <code>, <pre>. НЕ используй <h1>, <h2>, <p> и другие теги.
"""
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Ты опытный и добрый преподаватель английского языка. Твоя задача — научить ученика свободно общаться за год."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800,  # Увеличил, чтобы хватило на процент и дни
            timeout=30
        )
        content = response.choices[0].message.content
        # Удаляем опасные HTML-теги на всякий случай
        content = re.sub(r'</?h[1-6]>', '', content)
        content = re.sub(r'</?p>', '', content)
        content = re.sub(r'</?div>', '', content)
        return content
    except Exception as e:
        return f"❌ Ошибка при генерации урока: {str(e)}"

async def check_answer(question, user_answer):
    """Проверяет ответ ученика и даёт обратную связь"""
    
    prompt = f"""
{TEACHER_INSTRUCTION}

Задание: {question}
Ответ ученика: {user_answer}

Проверь ответ. Если есть ошибки, объясни их мягко и понятно.
Похвали за правильные моменты. Дай правильный вариант.

Важно: после проверки напиши:
- Процент правильности ответа (например "Точность: 75.00%")
- Сколько дней осталось до цели (примерно, на основе прогресса)

Ответ дай на русском языке, с эмодзи.
Форматируй текст с HTML-тегами для Telegram. Разрешены только: <b>, <i>, <u>, <s>, <code>, <pre>.
"""
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Ты добрый учитель английского. Не ругай за ошибки, а помогай. Всегда указывай прогресс."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=600,
            timeout=30
        )
        content = response.choices[0].message.content
        # Удаляем опасные HTML-теги на всякий случай
        content = re.sub(r'</?h[1-6]>', '', content)
        content = re.sub(r'</?p>', '', content)
        return content
    except Exception as e:
        return f"❌ Ошибка при проверке: {str(e)}"