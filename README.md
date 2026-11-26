# VanGhogVPN

Сайт и Telegram-бот для VPN-сервиса VanGhogVPN.

## Структура

- `site/index.html` — одностраничный сайт (один файл, без сборки). Ник бота и почта задаются в начале скрипта: `TG` и `MAIL`.
- `bot/vanghog_bot.py` — Telegram-бот (приём заявок и чеков, ручная выдача ключей).
- `bot/requirements.txt` — зависимости бота.

## Запуск бота

```
cd bot
pip install -r requirements.txt
```

Задайте переменные окружения (значения НЕ храните в репозитории):

```
BOT_TOKEN   токен от @BotFather
ADMIN_ID    числовой Telegram ID владельца (узнать: команда /myid у бота)
PAY_INFO    реквизиты, которые увидят клиенты
```

Затем: `python vanghog_bot.py`

## Безопасность

- Не коммитьте токен бота, пароли, ключи `vless://` и файл `trials.json`.
- Если токен случайно попал в репозиторий — отзовите его в @BotFather командой `/revoke`.
