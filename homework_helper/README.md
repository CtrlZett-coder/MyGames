# 📚 Репетитор — Telegram-бот

Присылаешь задание (фото или текстом) — бот объясняет по шагам, как его решать: какая тема, какое правило нужно, почему каждый шаг делается именно так. В конце даёт похожую задачу для самопроверки и может проверить твоё решение.

Работает с **DeepSeek** (по умолчанию) или с **Claude**.

## Что нужно

1. **Токен бота** — напиши [@BotFather](https://t.me/BotFather) в Telegram, команда `/newbot`, скопируй токен.
2. **Ключ нейросети:**
   - DeepSeek — на https://platform.deepseek.com (API Keys + пополнить баланс), или
   - Claude — на https://platform.claude.com.
3. Python 3.10+.

## Запуск с DeepSeek

```bash
cd homework_helper
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="токен от BotFather"
export DEEPSEEK_API_KEY="ключ DeepSeek"
python bot.py
```

⚠️ **Фото:** обычная модель DeepSeek (`deepseek-chat`) может не понимать картинки. Тогда бот ответит «перепиши задание текстом». Если у DeepSeek появится модель с поддержкой фото, укажи её: `export DEEPSEEK_MODEL="название-модели"`.

## Запуск с Claude (понимает фото)

```bash
export PROVIDER=claude
export ANTHROPIC_API_KEY="ключ Claude"
python bot.py
```

Бот работает, пока запущена программа. **Ключи не коммить в git!**

## Команды

| Что делаешь | Что происходит |
|---|---|
| `/start` | Приветствие |
| Фото задания (можно с подписью) | Подробный разбор |
| Текстовое сообщение | Вопрос по текущему заданию или новое задание текстом |
| `/new` | Начать новую тему |
