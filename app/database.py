import sqlite3
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot_data.db')

def get_db():
    """Подключение к базе данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Создание таблиц при первом запуске"""
    with get_db() as conn:
        # Таблица пользователей
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                joined_date TEXT,
                level TEXT DEFAULT 'beginner',
                total_xp INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                last_activity TEXT
            )
        ''')
        
        # Таблица прогресса по урокам
        conn.execute('''
            CREATE TABLE IF NOT EXISTS lessons_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                lesson_topic TEXT,
                completed BOOLEAN DEFAULT 0,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Таблица статистики ответов
        conn.execute('''
            CREATE TABLE IF NOT EXISTS answers_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                lesson_topic TEXT,
                question TEXT,
                user_answer TEXT,
                correct BOOLEAN,
                answered_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Таблица тем для изучения (новая)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                topic_name TEXT,
                topic_level TEXT,
                topic_index INTEGER,
                status TEXT DEFAULT 'pending',  -- 'pending', 'current', 'completed', 'repeating'
                completed_at TEXT,
                repeat_count INTEGER DEFAULT 0,
                last_repeated TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        conn.commit()

def get_or_create_user(user_id, first_name, username):
    """Получить пользователя или создать нового"""
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        
        if not user:
            now = datetime.datetime.now().isoformat()
            conn.execute('''
                INSERT INTO users (user_id, first_name, username, joined_date, last_activity)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, first_name, username, now, now))
            conn.commit()
            user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        
        return user

def update_streak(user_id):
    """Обновить серию дней"""
    with get_db() as conn:
        user = conn.execute('SELECT last_activity, current_streak, best_streak FROM users WHERE user_id = ?', (user_id,)).fetchone()
        
        if user and user['last_activity']:
            try:
                last = datetime.datetime.fromisoformat(user['last_activity'])
                now = datetime.datetime.now()
                today = now.date()
                last_date = last.date()
                
                # Если последняя активность была вчера
                if (today - last_date).days == 1:
                    new_streak = (user['current_streak'] or 0) + 1
                    best_streak = max(new_streak, user['best_streak'] or 0)
                    conn.execute('''
                        UPDATE users 
                        SET current_streak = ?, best_streak = ?, last_activity = ?
                        WHERE user_id = ?
                    ''', (new_streak, best_streak, now.isoformat(), user_id))
                
                # Если сегодня уже был
                elif (today - last_date).days == 0:
                    pass  # ничего не меняем
                
                # Если пропустил день
                else:
                    conn.execute('''
                        UPDATE users 
                        SET current_streak = 1, last_activity = ?
                        WHERE user_id = ?
                    ''', (now.isoformat(), user_id))
            except:
                # Если ошибка с датой, просто обновляем активность
                conn.execute('''
                    UPDATE users 
                    SET last_activity = ?
                    WHERE user_id = ?
                ''', (datetime.datetime.now().isoformat(), user_id))
            
            conn.commit()

def add_xp(user_id, xp_amount):
    """Добавить очки опыта"""
    with get_db() as conn:
        conn.execute('UPDATE users SET total_xp = total_xp + ? WHERE user_id = ?', (xp_amount, user_id))
        conn.commit()

def save_answer(user_id, lesson_topic, question, user_answer, correct):
    """Сохранить ответ в историю"""
    with get_db() as conn:
        conn.execute('''
            INSERT INTO answers_history (user_id, lesson_topic, question, user_answer, correct, answered_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, lesson_topic, question, user_answer, 1 if correct else 0, datetime.datetime.now().isoformat()))
        conn.commit()

def complete_lesson(user_id, lesson_topic):
    """Отметить урок как пройденный"""
    with get_db() as conn:
        conn.execute('''
            INSERT INTO lessons_progress (user_id, lesson_topic, completed, completed_at)
            VALUES (?, ?, 1, ?)
        ''', (user_id, lesson_topic, datetime.datetime.now().isoformat()))
        conn.commit()

def get_user_stats(user_id):
    """Получить статистику пользователя"""
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        
        # Количество пройденных уроков
        lessons = conn.execute('SELECT COUNT(*) as count FROM lessons_progress WHERE user_id = ?', (user_id,)).fetchone()
        
        # Статистика ответов
        answers = conn.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) as correct
            FROM answers_history 
            WHERE user_id = ?
        ''', (user_id,)).fetchone()
        
        return {
            'user': user,
            'lessons_count': lessons['count'] if lessons else 0,
            'total_answers': answers['total'] if answers and answers['total'] else 0,
            'correct_answers': answers['correct'] if answers and answers['correct'] else 0
        }

# === НОВЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ТЕМАМИ ===

def init_user_topics(user_id):
    """Инициализирует темы для нового пользователя"""
    topics = [
        (1, "to be", "beginner"),
        (2, "present continuous", "beginner"),
        (3, "present simple", "beginner"),
        (4, "past simple", "beginner"),
        (5, "future simple", "beginner"),
        (6, "modal verbs (can, must, should)", "beginner"),
        (7, "comparatives and superlatives", "beginner"),
        (8, "prepositions of time and place", "beginner"),
        (9, "countable and uncountable nouns", "beginner"),
        (10, "there is/there are", "beginner"),
        (11, "present perfect", "intermediate"),
        (12, "past continuous", "intermediate"),
        (13, "future forms (going to, will)", "intermediate"),
        (14, "conditionals 0 and 1", "intermediate"),
        (15, "passive voice", "intermediate"),
        (16, "phrasal verbs basic", "intermediate"),
        (17, "relative clauses", "intermediate"),
        (18, "reported speech", "intermediate"),
        (19, "gerund and infinitive", "intermediate"),
        (20, "quantifiers", "intermediate"),
        (21, "present perfect continuous", "advanced"),
        (22, "past perfect", "advanced"),
        (23, "future perfect", "advanced"),
        (24, "conditionals 2 and 3", "advanced"),
        (25, "mixed conditionals", "advanced"),
        (26, "advanced phrasal verbs", "advanced"),
        (27, "inversion", "advanced"),
        (28, "subjunctive mood", "advanced"),
        (29, "collocations and idioms", "advanced"),
        (30, "advanced discussion topics", "advanced")
    ]
    
    with get_db() as conn:
        # Проверяем, есть ли уже темы у пользователя
        existing = conn.execute('SELECT COUNT(*) as count FROM user_topics WHERE user_id = ?', (user_id,)).fetchone()
        
        if existing['count'] == 0:
            for idx, topic, level in topics:
                # Первая тема будет current, остальные pending
                status = 'current' if idx == 1 else 'pending'
                conn.execute('''
                    INSERT INTO user_topics (user_id, topic_name, topic_level, topic_index, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, topic, level, idx, status))
            conn.commit()
            return True
    return False

def get_current_topic(user_id):
    """Получает текущую тему для изучения"""
    with get_db() as conn:
        topic = conn.execute('''
            SELECT * FROM user_topics 
            WHERE user_id = ? AND status = 'current'
            ORDER BY topic_index LIMIT 1
        ''', (user_id,)).fetchone()
        
        if not topic:
            # Если нет текущей темы, берём следующую невыполненную
            topic = conn.execute('''
                SELECT * FROM user_topics 
                WHERE user_id = ? AND status = 'pending'
                ORDER BY topic_index LIMIT 1
            ''', (user_id,)).fetchone()
            
            if topic:
                conn.execute('UPDATE user_topics SET status = "current" WHERE id = ?', (topic['id'],))
                conn.commit()
                topic = conn.execute('SELECT * FROM user_topics WHERE id = ?', (topic['id'],)).fetchone()
        
        return topic

def complete_topic(user_id, topic_id):
    """Отмечает тему как пройденную"""
    with get_db() as conn:
        conn.execute('''
            UPDATE user_topics 
            SET status = 'completed', completed_at = ?
            WHERE id = ? AND user_id = ?
        ''', (datetime.datetime.now().isoformat(), topic_id, user_id))
        conn.commit()

def get_completed_topics(user_id):
    """Возвращает список пройденных тем"""
    with get_db() as conn:
        topics = conn.execute('''
            SELECT * FROM user_topics 
            WHERE user_id = ? AND status = 'completed'
            ORDER BY topic_index
        ''', (user_id,)).fetchall()
        return topics

def get_all_topics(user_id):
    """Возвращает все темы пользователя"""
    with get_db() as conn:
        topics = conn.execute('''
            SELECT * FROM user_topics 
            WHERE user_id = ?
            ORDER BY topic_index
        ''', (user_id,)).fetchall()
        return topics

def start_repeating_topic(user_id, topic_id):
    """Начинает повторение темы"""
    with get_db() as conn:
        # Сначала сбрасываем текущую тему, если она есть
        current = conn.execute('SELECT id FROM user_topics WHERE user_id = ? AND status = "current"', (user_id,)).fetchone()
        if current:
            conn.execute('UPDATE user_topics SET status = "pending" WHERE id = ?', (current['id'],))
        
        # Отмечаем выбранную тему как повторяемую
        conn.execute('''
            UPDATE user_topics 
            SET status = 'repeating', repeat_count = repeat_count + 1, last_repeated = ?
            WHERE id = ? AND user_id = ?
        ''', (datetime.datetime.now().isoformat(), topic_id, user_id))
        conn.commit()

def get_next_pending_topic(user_id):
    """Получает следующую ожидающую тему"""
    with get_db() as conn:
        topic = conn.execute('''
            SELECT * FROM user_topics 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY topic_index LIMIT 1
        ''', (user_id,)).fetchone()
        return topic

def get_repeating_topics(user_id):
    """Возвращает темы на повторении"""
    with get_db() as conn:
        topics = conn.execute('''
            SELECT * FROM user_topics 
            WHERE user_id = ? AND status = 'repeating'
            ORDER BY last_repeated
        ''', (user_id,)).fetchall()
        return topics

def calculate_progress_percentage(user_id):
    """Вычисляет процент прогресса"""
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) as count FROM user_topics WHERE user_id = ?', (user_id,)).fetchone()
        completed = conn.execute('SELECT COUNT(*) as count FROM user_topics WHERE user_id = ? AND status = "completed"', (user_id,)).fetchone()
        
        if total['count'] > 0:
            percentage = (completed['count'] / total['count']) * 100
            return round(percentage, 2)
        return 0.0

def reset_to_next_topic(user_id, current_topic_id):
    """Сбрасывает текущую тему и переходит к следующей (на случай ошибок)"""
    with get_db() as conn:
        # Отмечаем текущую как pending (не пройденную)
        conn.execute('''
            UPDATE user_topics 
            SET status = 'pending'
            WHERE id = ? AND user_id = ?
        ''', (current_topic_id, user_id))
        
        # Берём следующую
        next_topic = conn.execute('''
            SELECT * FROM user_topics 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY topic_index LIMIT 1
        ''', (user_id,)).fetchone()
        
        if next_topic:
            conn.execute('UPDATE user_topics SET status = "current" WHERE id = ?', (next_topic['id'],))
            conn.commit()
            return next_topic
        conn.commit()
        return None