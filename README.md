# Перукарня «Найкраща» — Telegram-бот

Каркас Telegram-бота для перукарні в Києві. Інтерфейс бота — українською мовою.
На цьому етапі реалізовано меню, навігацію, статичні розділи та заглушки.
Бази даних, онлайн-запису й оплати ще немає.

## Структура

```text
bot-2/
├── bot.py              # точка входу: Application, polling, запуск health-сервера
├── config.py           # токен, ADMIN_CHAT_ID, PORT, контактні дані, послуги
├── texts.py            # українські тексти та підписи кнопок
├── keyboards.py        # inline-клавіатури та callback-константи
├── web.py              # Flask health-сервер для Render
├── handlers/
│   ├── __init__.py     # реєстрація всіх обробників
│   ├── common.py       # /start, /menu, /help, головне меню, error handler
│   ├── user.py         # запис, послуги, мої записи, контакти
│   └── admin.py        # адмін-панель і три розділи
├── requirements.txt
├── runtime.txt
├── render.yaml
├── .env.example
├── .gitignore
└── README.md
```

## Локальний запуск

Потрібен Python 3.11+.

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Встановлення залежностей:

```bash
pip install -r requirements.txt
```

Змінні середовища:

```powershell
$env:BOT_TOKEN = "токен_від_BotFather"
$env:ADMIN_CHAT_ID = "ваш_telegram_id"
python bot.py
```

`ADMIN_CHAT_ID` необов'язковий: без нього бот працює, але адмін-панель недоступна.
`PORT` теж необов'язковий; локально health-сервер використовує 10000.
Файл `.env.example` — лише шаблон; бот не завантажує `.env` автоматично, тому
змінні треба задати в терміналі або в налаштуваннях хостингу.

Щоб дізнатися свій `ADMIN_CHAT_ID`, напишіть боту будь-яке повідомлення та відкрийте
`https://api.telegram.org/bot<ТОКЕН>/getUpdates`. Значення `message.from.id` — це ваш ID.

## Render

У репозиторії є `render.yaml`. Створіть Blueprint або Web Service вручну.
Якщо в репозиторії є інші проєкти, вкажіть **Root Directory: `bot-2`**.

- Build Command: `pip install -r requirements.txt`
- Start Command: `python bot.py`
- Health Check Path: `/health`
- Environment:
  - `BOT_TOKEN` — токен від BotFather;
  - `ADMIN_CHAT_ID` — ваш Telegram ID;
  - `PYTHON_VERSION=3.11.9` (або інша версія 3.11+).

Flask-сервер працює в окремому daemon-потоці й слухає `0.0.0.0:$PORT`.
Це потрібно, щоб Render бачив відкритий порт. Основний бот працює через
`run_polling(drop_pending_updates=True)`.

На безкоштовному плані Render сервіс може «засинати» без трафіку. Для постійної
роботи потрібен платний інстанс або зовнішній пінг health-ендпоінта.

## Що замінити перед реальним запуском

Демонстраційні дані зібрані в `config.py`:

- `ADDRESS`, `PHONE`, `PHONE_URI`, `INSTAGRAM_URL`, `WORKING_HOURS`;
- `SERVICES` — перелік послуг і цін.

Поточні адреса й телефон позначені як демо. Замініть їх на реальні дані перукарні.

## Що реалізовано

- Головне меню: «Записатися», «Послуги та ціни», «Мої записи», «Адреса та контакти».
- Адмін-панель: «Заявки», «Розклад», «Налаштування».
- Навігація «Назад» і «Головне меню».
- Заглушки для функцій, які ще не реалізовані.
- Перевірка доступу до адмін-панелі за `ADMIN_CHAT_ID`.
- `/start`, `/menu`, `/help`, `/admin`.
- Health-сервер для Render.
