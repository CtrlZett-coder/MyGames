"""Block Blast solver Telegram bot.

Flow per chat:
  1. /start -> show menu.
  2. Edit the 8x8 board with an inline-keyboard grid (tap to toggle a cell).
  3. Pick the 3 pieces you were dealt from a paginated catalog.
  4. Bot brute-forces every order/placement of the 3 pieces and replies with
     the best sequence (most points + keeps the board open), step by step.
  5. "Apply & continue" carries the resulting board into the next round.

Session state lives in memory, keyed by chat_id (see SESSIONS below) -- it
is lost on restart, which is fine for a single-process assistant bot.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import render
import solver
from pieces import PIECES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("block_blast_bot")

PAGE_SIZE = 8
TOTAL_PAGES = math.ceil(len(PIECES) / PAGE_SIZE)

SESSIONS: dict[int, dict] = {}


def get_session(chat_id: int) -> dict:
    if chat_id not in SESSIONS:
        SESSIONS[chat_id] = {"board": solver.empty_board(), "mode": "editing", "selected": [], "page": 0}
    return SESSIONS[chat_id]


def build_board_keyboard(board: int) -> InlineKeyboardMarkup:
    rows = []
    for r in range(solver.SIZE):
        row = []
        for c in range(solver.SIZE):
            filled = board & (1 << solver.idx(r, c))
            label = render.CELL_FILLED if filled else render.CELL_EMPTY
            row.append(InlineKeyboardButton(label, callback_data=f"cell:{r}:{c}"))
        rows.append(row)
    rows.append([
        InlineKeyboardButton("🧹 Очистить поле", callback_data="board:clear"),
        InlineKeyboardButton("✅ Поле готово", callback_data="board:done"),
    ])
    return InlineKeyboardMarkup(rows)


def board_editor_text(board: int) -> str:
    filled = bin(board).count("1")
    return (
        "✏️ *Редактирование поля* (8x8)\n"
        "Нажимайте на клетки, чтобы отметить занятые (⬛) — как в текущей партии.\n"
        f"Занято клеток: {filled}/64\n\n"
        + render.render_grid(board)
    )


def build_picker_keyboard(page: int, selected: list[str]) -> InlineKeyboardMarkup:
    start = page * PAGE_SIZE
    page_pieces = PIECES[start:start + PAGE_SIZE]
    rows = []
    for i in range(0, len(page_pieces), 2):
        row = []
        for p in page_pieces[i:i + 2]:
            mark = "✓ " if p["code"] in selected else ""
            row.append(InlineKeyboardButton(f"{mark}{p['code']}", callback_data=f"piece:{p['code']}"))
        rows.append(row)
    rows.append([
        InlineKeyboardButton("◀️", callback_data="page:prev"),
        InlineKeyboardButton(f"{page + 1}/{TOTAL_PAGES}", callback_data="noop"),
        InlineKeyboardButton("▶️", callback_data="page:next"),
    ])
    rows.append([
        InlineKeyboardButton("↩️ Убрать последнюю", callback_data="piece:undo"),
        InlineKeyboardButton("🔙 К редактированию поля", callback_data="back:board"),
    ])
    return InlineKeyboardMarkup(rows)


def picker_text(page: int, selected: list[str]) -> str:
    start = page * PAGE_SIZE
    page_pieces = PIECES[start:start + PAGE_SIZE]
    legend = render.render_piece_legend([p["code"] for p in page_pieces])
    chosen = ", ".join(selected) if selected else "—"
    return (
        "🧩 *Выберите 3 выданные фигуры*\n"
        f"Выбрано ({len(selected)}/3): {chosen}\n\n"
        "Фигуры на этой странице:\n"
        f"```\n{legend}\n```"
    )


async def show_board_editor(query_or_message, board: int, edit: bool = True):
    text = board_editor_text(board)
    markup = build_board_keyboard(board)
    if edit:
        await query_or_message.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await query_or_message.reply_text(text, reply_markup=markup, parse_mode="Markdown")


async def show_picker(query, session: dict):
    text = picker_text(session["page"], session["selected"])
    markup = build_picker_keyboard(session["page"], session["selected"])
    await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    get_session(chat_id)
    text = (
        "🎮 *Block Blast Solver*\n\n"
        "Помогу найти лучший ход для текущей партии: отмечаете занятые клетки "
        "поля 8x8, выбираете 3 выданные фигуры — а бот переберёт все варианты "
        "порядка и расположения и подскажет, куда их ставить для максимума очков "
        "и расчисток линий.\n\n"
        "Команды:\n"
        "/round — начать новый раунд (редактировать поле)\n"
        "/reset — сбросить поле и начать с пустого\n"
        "/help — подсказка"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
    await show_board_editor(update.message, get_session(chat_id)["board"], edit=False)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "1) Отметьте на сетке клетки, занятые на вашем поле сейчас.\n"
        "2) Нажмите «Поле готово».\n"
        "3) Выберите ровно 3 фигуры, которые вам выдала игра (листайте страницы ◀️▶️).\n"
        "4) Бот посчитает лучший порядок установки и пришлёт схему ходов.\n"
        "5) «Применить и продолжить» переносит результат в следующий раунд.\n\n"
        "Набор фигур — стандартные полимино (линии 1-5, квадраты, L/J/T/S/Z, "
        "плюс, уголок, U-образная). Если в вашей версии игры фигуры отличаются, "
        "их легко добавить в pieces.py."
    )


async def round_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    session["mode"] = "editing"
    session["selected"] = []
    session["page"] = 0
    await show_board_editor(update.message, session["board"], edit=False)


async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    SESSIONS[chat_id] = {"board": solver.empty_board(), "mode": "editing", "selected": [], "page": 0}
    await show_board_editor(update.message, SESSIONS[chat_id]["board"], edit=False)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    session = get_session(chat_id)
    data = query.data
    await query.answer()

    if data == "noop":
        return

    if data.startswith("cell:"):
        _, r, c = data.split(":")
        bit = 1 << solver.idx(int(r), int(c))
        session["board"] ^= bit
        await query.edit_message_text(board_editor_text(session["board"]), reply_markup=build_board_keyboard(session["board"]), parse_mode="Markdown")
        return

    if data == "board:clear":
        session["board"] = solver.empty_board()
        await query.edit_message_text(board_editor_text(session["board"]), reply_markup=build_board_keyboard(session["board"]), parse_mode="Markdown")
        return

    if data == "board:done":
        session["mode"] = "picking"
        session["selected"] = []
        session["page"] = 0
        await show_picker(query, session)
        return

    if data == "back:board":
        session["mode"] = "editing"
        await query.edit_message_text(board_editor_text(session["board"]), reply_markup=build_board_keyboard(session["board"]), parse_mode="Markdown")
        return

    if data == "page:prev":
        session["page"] = (session["page"] - 1) % TOTAL_PAGES
        await show_picker(query, session)
        return

    if data == "page:next":
        session["page"] = (session["page"] + 1) % TOTAL_PAGES
        await show_picker(query, session)
        return

    if data == "piece:undo":
        if session["selected"]:
            session["selected"].pop()
        await show_picker(query, session)
        return

    if data.startswith("piece:"):
        code = data.split(":", 1)[1]
        if len(session["selected"]) < 3:
            session["selected"].append(code)
        if len(session["selected"]) < 3:
            await show_picker(query, session)
        else:
            await solve_and_reply(query, session)
        return

    if data == "solve:apply":
        solution = session.get("solution")
        if solution:
            session["board"] = solution["final_board"]
        session["mode"] = "picking"
        session["selected"] = []
        session["page"] = 0
        await show_picker(query, session)
        return

    if data == "solve:edit_board":
        session["mode"] = "editing"
        await query.edit_message_text(board_editor_text(session["board"]), reply_markup=build_board_keyboard(session["board"]), parse_mode="Markdown")
        return


async def solve_and_reply(query, session: dict):
    await query.edit_message_text("🤔 Считаю варианты ходов...")
    board_before = session["board"]
    codes = list(session["selected"])
    loop = asyncio.get_running_loop()
    solution = await loop.run_in_executor(None, solver.solve, board_before, codes)

    if solution is None:
        await query.edit_message_text(
            "😬 Ни одно из 3 фигур не помещается на поле в любом порядке — раунд проигрышный.\n"
            "Используйте /round чтобы отредактировать поле или фигуры заново."
        )
        session["mode"] = "editing"
        return

    session["solution"] = {"final_board": solution.final_board}
    text = render.render_solution(board_before, solution)
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Применить и продолжить", callback_data="solve:apply")],
        [InlineKeyboardButton("✏️ Изменить поле", callback_data="solve:edit_board")],
    ])
    await query.edit_message_text(text, reply_markup=markup)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN environment variable before starting the bot.")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("round", round_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CallbackQueryHandler(on_callback))

    log.info("Block Blast solver bot starting (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
