"""VanGhogVPN Telegram-бот (версия 1, ручная выдача ключей).

Как работает:
  клиент выбирает тариф -> получает реквизиты -> присылает чек ->
  чек приходит вам с кнопками «Подтвердить / Отклонить» ->
  после подтверждения вы создаёте клиента в 3x-ui и отправляете ключ командой
  /key ID_КЛИЕНТА ваш_ключ_или_ссылка

Запуск:
  pip install "python-telegram-bot>=21"
  export BOT_TOKEN="токен от @BotFather"
  export ADMIN_ID="ваш числовой Telegram ID (узнайте командой /myid у бота)"
  export PAY_INFO="Карта: XXXX XXXX XXXX XXXX, получатель: Имя Ф. Или номер для СБП"
  python vanghog_bot.py
"""
import html
import json
import logging
import os
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])
PAY_INFO = os.environ.get("PAY_INFO", "Реквизиты пришлёт администратор.")

# Минимум логов: только ошибки, без содержимого сообщений.
logging.basicConfig(level=logging.ERROR)

PLANS = {
    "week": ("Неделя", 99),
    "month": ("Месяц", 199),
    "year": ("Год", 1999),
}
TRIALS = Path("trials.json")  # хранит только ID тех, кто уже брал пробную неделю


def trial_used(uid: int) -> bool:
    try:
        return uid in json.loads(TRIALS.read_text())
    except (FileNotFoundError, ValueError):
        return False


def mark_trial(uid: int) -> None:
    try:
        ids = json.loads(TRIALS.read_text())
    except (FileNotFoundError, ValueError):
        ids = []
    if uid not in ids:
        ids.append(uid)
        TRIALS.write_text(json.dumps(ids))


def menu() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton("Бесплатная неделя", callback_data="plan:trial")]]
    for pid, (name, price) in PLANS.items():
        rows.append([InlineKeyboardButton(f"{name} — {price} ₽", callback_data=f"plan:{pid}")])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pid = ctx.args[0] if ctx.args else None
    if pid in PLANS:  # пришли с сайта: сразу показываем оплату выбранного тарифа
        name, price = PLANS[pid]
        ctx.user_data["plan"] = pid
        await update.message.reply_text(
            f"Тариф «{name}»: {price} ₽.\n\n{PAY_INFO}\n\n"
            "После перевода пришлите сюда скриншот или файл чека."
        )
        return
    await update.message.reply_text(
        "Добро пожаловать в VanGhogVPN 🌌\nБез логов, до 3 устройств, первая неделя бесплатно.\nВыберите тариф:",
        reply_markup=menu(),
    )


async def myid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ваш ID: {update.effective_user.id}")


async def choose(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pid = q.data.split(":", 1)[1]
    uid = q.from_user.id

    if pid == "trial":
        if trial_used(uid):
            await q.message.reply_text("Пробная неделя уже была использована. Выберите платный тариф:", reply_markup=menu())
            return
        mark_trial(uid)
        await ctx.bot.send_message(
            ADMIN_ID, f"Запрос бесплатной недели от ID {uid}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Подтвердить", callback_data=f"ok:{uid}:trial"),
                InlineKeyboardButton("Отклонить", callback_data=f"no:{uid}"),
            ]]),
        )
        await q.message.reply_text("Заявка отправлена. Ключ придёт сюда после проверки.")
        return

    if pid not in PLANS:
        return
    name, price = PLANS[pid]
    ctx.user_data["plan"] = pid
    await q.message.reply_text(
        f"Тариф «{name}»: {price} ₽.\n\n{PAY_INFO}\n\n"
        "После перевода пришлите сюда скриншот или файл чека."
    )


async def receipt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pid = ctx.user_data.get("plan")
    if pid not in PLANS:
        await update.message.reply_text("Сначала выберите тариф:", reply_markup=menu())
        return
    name, price = PLANS[pid]
    uid = update.effective_user.id
    await ctx.bot.copy_message(
        ADMIN_ID, update.effective_chat.id, update.message.message_id,
        caption=f"Оплата: «{name}», {price} ₽, от ID {uid}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Подтвердить", callback_data=f"ok:{uid}:{pid}"),
            InlineKeyboardButton("Отклонить", callback_data=f"no:{uid}"),
        ]]),
    )
    ctx.user_data.pop("plan", None)
    await update.message.reply_text("Чек получен. Проверим и пришлём ключ.")


async def decision(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:  # только владелец
        await q.answer()
        return
    await q.answer()
    parts = q.data.split(":")
    uid = int(parts[1])
    await q.edit_message_reply_markup(reply_markup=None)
    if parts[0] == "ok":
        await ctx.bot.send_message(uid, "Оплата подтверждена ✅ Скоро пришлём ключ.")
        await ctx.bot.send_message(ADMIN_ID, f"Создайте клиента в 3x-ui и отправьте ключ:\n/key {uid} ключ")
    else:
        await ctx.bot.send_message(uid, "Не удалось подтвердить оплату. Напишите администратору.")


async def key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(ctx.args) < 2 or not ctx.args[0].isdigit():
        await update.message.reply_text("Формат: /key ID_КЛИЕНТА ключ")
        return
    uid = int(ctx.args[0])
    value = html.escape(" ".join(ctx.args[1:]))
    await ctx.bot.send_message(
        uid,
        f"Ваш ключ:\n<code>{value}</code>\n\nСкопируйте его и добавьте в приложение-клиент "
        "(например, Hiddify или v2rayNG). До 3 устройств.",
        parse_mode="HTML",
    )
    await update.message.reply_text("Ключ отправлен ✅")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("key", key))
    app.add_handler(CallbackQueryHandler(choose, pattern=r"^plan:"))
    app.add_handler(CallbackQueryHandler(decision, pattern=r"^(ok|no):"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receipt))
    app.run_polling()


if __name__ == "__main__":
    main()
