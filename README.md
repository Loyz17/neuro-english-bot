# Aiogram Bot Skeleton

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Aiogram](https://img.shields.io/badge/aiogram-v3-green.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![views](https://visitor-badge.laobi.icu/badge?page_id=mrkorzun&left_text=views)



🚀 **Aiogram Bot Skeleton** — это минималистичный, но расширяемый шаблон для создания Telegram-ботов на **aiogram v3**.  
Он экономит время при старте новых проектов: вместо рутинной сборки каркаса — готовый фундамент, который можно адаптировать под любые задачи.

## 🤝 Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## ✨ Возможности
- Чистая структура проекта:
  - `main.py` — запуск и конфигурация.
  - `handlers.py` — все хендлеры.
  - `keyboards.py` — кнопки и клавиатуры.
  - `states.py` — FSM состояния.
- Поддержка команд `/start` и `/help`.
- Пример FSM-формы (имя + возраст).
- Inline/Reply клавиатуры.
- Конфигурация через `.env`.
- MIT-лицензия.

## 📂 Структура проекта
```text
aiogram-bot-skeleton/
├─ main.py
├─ handlers.py
├─ keyboards.py
├─ states.py
├─ requirements.txt
├─ .env.example
├─ .gitignore
├─ README.md
└─ LICENSE
```

---

## ⚡ Быстрый старт

```bash
# 1. Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Unix/Mac
.venv\Scripts\activate     # Windows
```

# 2. Установить зависимости
```bash
pip install -r requirements.txt
```

# 3. Добавить токен в .env
```bash
cp .env.example .env
# впиши BOT_TOKEN=xxx
```

# 4. Запустить бота
```bash
python main.py
```

## Технологии
- Python 3.10+
- aiogram v3
- python-dotenv

## Дорожная карта

Проект будет обновляться и развиваться. В будущих релизах планируется:
- Поддержка баз данных (SQLite/Postgres через SQLAlchemy).
- Модульная структура роутеров.
- Локализация (i18n).
- Dockerfile + docker-compose.
- GitHub Actions (линтинг, тесты, релизы).
- Интеграция Redis для FSM.
