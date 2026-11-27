"""Telegram-бот «Репетитор»: присылаешь фото задания — получаешь
подробный разбор, как его решать, и можешь задавать уточняющие вопросы.

Запуск:
    export TELEGRAM_BOT_TOKEN=...   # от @BotFather
    export ANTHROPIC_API_KEY=...    # с platform.claude.com
    python bot.py
"""

import base64
import logging
import os

import anthropic
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("homework_helper")

MODEL = "claude-opus-5-5"
MAX_HISTORY = 20          # сообщений в одном разговоре, потом начинаем заново
TELEGRAM_LIMIT = 4000     # Telegram режет сообщения длиннее 4096 символов

SYSTEM_PROMPT = """Ты — доброжелательный репетитор для школьника. Тебе присылают \
фото или текст задания. Твоя цель — чтобы ученик ПОНЯЛ, как решать такие задачи, \
и в следующий раз справился сам.

Как отвечать:
1. Коротко скажи, что это за тип задачи и какая тема/правило тут нужно.
2. Напомни нужное правило или формулу простыми словами.
3. Разбери решение по шагам, объясняя КАЖДЫЙ шаг: что делаем и почему.
4. В конце дай ответ и предложи похожую задачу для самопроверки (без ответа — \
пусть ученик попробует сам и пришлёт решение, ты проверишь).

Если на фото несколько заданий — подробно разбери первое, а для остальных \
дай подсказку, с чего начать, и предложи ученику попробовать самому.
Если фото нечитаемое — попроси переснять.
Пиши по-русски, простым языком. Telegram не показывает LaTeX и markdown, \
поэтому пиши формулы обычным текстом (x^2, корень(9), 3/4) и не используй \
символы * и # для оформления."""

client = anthropic.AsyncAnthropic()


def split_message(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Режет длинный ответ на куски, стараясь резать по абзацам."""
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        parts.append(text)
    return parts


async def ask_claude(history: list[dict]) -> str:
    response = await client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=history,
    )
    if response.stop_reason == "refusal":
        return "Не могу помочь с этим запросом. Попробуй прислать другое задание."
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if response.stop_reason == "max_tokens":
        text += "\n\n(Ответ получился слишком длинным и обрезался — спроси «продолжи».)"
    return text or "Что-то пошло не так, попробуй ещё раз."


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE, content) -> None:
    history: list[dict] = context.chat_data.setdefault("history", [])
    if len(history) >= MAX_HISTORY:
        history.clear()
    history.append({"role": "user", "content": content})

    await update.effective_chat.send_action(ChatAction.TYPING)
    try:
        answer = await ask_claude(history)
    except anthropic.RateLimitError:
        history.pop()
        await update.message.reply_text("Слишком много запросов, подожди минутку.")
        return
    except anthropic.APIStatusError as e:
        history.pop()
        log.exception("API error %s", e.status_code)
        await update.message.reply_text("Ошибка сервера, попробуй ещё раз.")
        return
    except anthropic.APIConnectionError:
        history.pop()
        await update.message.reply_text("Нет связи с сервером, попробуй позже.")
        return

    # Храним только текст ответа: так историю можно безопасно обрезать.
    history.append({"role": "assistant", "content": answer})
    for part in split_message(answer):
        await update.message.reply_text(part)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я репетитор.\n\n"
        "Пришли фото задания (или напиши его текстом) — я объясню, как его "
        "решать, по шагам. Потом можешь спрашивать «а почему так?» или "
        "прислать своё решение похожей задачи на проверку.\n\n"
        "/new — начать новую тему"
    )


async def new_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data["history"] = []
    await update.message.reply_text("Окей, начинаем заново. Присылай задание!")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Новое фото = новое задание, старый разговор не нужен.
    context.chat_data["history"] = []
    photo = update.message.photo[-1]  # самое большое разрешение
    file = await photo.get_file()
    data = bytes(await file.download_as_bytearray())
    caption = update.message.caption or "Объясни, как решать это задание."
    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64.standard_b64encode(data).decode("utf-8"),
            },
        },
        {"type": "text", "text": caption},
    ]
    await reply(update, context, content)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply(update, context, update.message.text)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Задай переменную окружения TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_topic))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    log.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
