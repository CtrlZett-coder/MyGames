"""Telegram-бот «Репетитор»: присылаешь фото задания — получаешь
подробный разбор, как его решать, и можешь задавать уточняющие вопросы.

Работает с двумя нейросетями на выбор (переменная PROVIDER):
    PROVIDER=deepseek  — DeepSeek (по умолчанию), нужен DEEPSEEK_API_KEY
    PROVIDER=claude    — Claude, нужен ANTHROPIC_API_KEY

Запуск:
    export TELEGRAM_BOT_TOKEN=...   # от @BotFather
    export DEEPSEEK_API_KEY=...     # с platform.deepseek.com
    python bot.py
"""

import base64
import logging
import os

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

PROVIDER = os.environ.get("PROVIDER", "deepseek").lower()
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
CLAUDE_MODEL = "claude-opus-5-5"

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

NO_PHOTO_TEXT = (
    "Эта нейросеть не принимает фото. Перепиши задание текстом "
    "и пришли сообщением — я разберу."
)


class ProviderError(Exception):
    """Ошибка нейросети, текст которой можно показать пользователю."""


# ---------- Общий формат истории ----------
# Сообщение пользователя: {"role": "user", "text": str, "image": bytes | None}
# Ответ:                  {"role": "assistant", "text": str}


# ---------- DeepSeek (совместим с OpenAI API) ----------

if PROVIDER == "deepseek":
    import openai

    deepseek = openai.AsyncOpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url=DEEPSEEK_BASE_URL
    )

    async def ask(history: list[dict]) -> str:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in history:
            if m.get("image"):
                b64 = base64.standard_b64encode(m["image"]).decode("utf-8")
                content = [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": m["text"]},
                ]
            else:
                content = m["text"]
            messages.append({"role": m["role"], "content": content})

        try:
            response = await deepseek.chat.completions.create(
                model=DEEPSEEK_MODEL, messages=messages, max_tokens=8000
            )
        except openai.RateLimitError:
            raise ProviderError("Слишком много запросов, подожди минутку.")
        except openai.AuthenticationError:
            raise ProviderError("Неверный DEEPSEEK_API_KEY — проверь ключ.")
        except openai.BadRequestError as e:
            if history[-1].get("image"):
                log.warning("DeepSeek отклонил фото: %s", e)
                raise ProviderError(NO_PHOTO_TEXT)
            log.exception("DeepSeek 400")
            raise ProviderError("Нейросеть не приняла запрос, попробуй иначе.")
        except openai.APIStatusError as e:
            if e.status_code == 402:
                raise ProviderError("На балансе DeepSeek закончились деньги.")
            log.exception("DeepSeek error %s", e.status_code)
            raise ProviderError("Ошибка сервера, попробуй ещё раз.")
        except openai.APIConnectionError:
            raise ProviderError("Нет связи с сервером, попробуй позже.")

        choice = response.choices[0]
        text = (choice.message.content or "").strip()
        if choice.finish_reason == "length":
            text += "\n\n(Ответ обрезался — напиши «продолжи».)"
        return text


# ---------- Claude ----------

elif PROVIDER == "claude":
    import anthropic

    claude = anthropic.AsyncAnthropic()

    async def ask(history: list[dict]) -> str:
        messages = []
        for m in history:
            if m.get("image"):
                content = [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/jpeg",
                        "data": base64.standard_b64encode(m["image"]).decode("utf-8"),
                    }},
                    {"type": "text", "text": m["text"]},
                ]
            else:
                content = m["text"]
            messages.append({"role": m["role"], "content": content})

        try:
            response = await claude.beta.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                output_config={"effort": "medium"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                messages=messages,
            )
        except anthropic.RateLimitError:
            raise ProviderError("Слишком много запросов, подожди минутку.")
        except anthropic.APIStatusError as e:
            log.exception("Claude error %s", e.status_code)
            raise ProviderError("Ошибка сервера, попробуй ещё раз.")
        except anthropic.APIConnectionError:
            raise ProviderError("Нет связи с сервером, попробуй позже.")

        if response.stop_reason == "refusal":
            return "Не могу помочь с этим запросом. Попробуй прислать другое задание."
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        if response.stop_reason == "max_tokens":
            text += "\n\n(Ответ обрезался — напиши «продолжи».)"
        return text

else:
    raise SystemExit(f"Неизвестный PROVIDER={PROVIDER!r}, нужно deepseek или claude")


# ---------- Telegram ----------

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


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE,
                text: str, image: bytes | None = None) -> None:
    history: list[dict] = context.chat_data.setdefault("history", [])
    if len(history) >= MAX_HISTORY:
        history.clear()
    history.append({"role": "user", "text": text, "image": image})

    await update.effective_chat.send_action(ChatAction.TYPING)
    try:
        answer = await ask(history)
    except ProviderError as e:
        history.pop()
        await update.message.reply_text(str(e))
        return

    answer = answer or "Что-то пошло не так, попробуй ещё раз."
    history.append({"role": "assistant", "text": answer})
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
    await reply(update, context, caption, image=data)


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
    log.info("Бот запущен, нейросеть: %s", PROVIDER)
    app.run_polling()


if __name__ == "__main__":
    main()
