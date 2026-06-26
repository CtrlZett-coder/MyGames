"""Plain-text/emoji rendering helpers for Telegram messages (no telegram deps)."""

from __future__ import annotations

from pieces import get_piece
from solver import SIZE, idx

CELL_EMPTY = "⬜"
CELL_FILLED = "⬛"
STEP_EMOJI = ["1️⃣", "2️⃣", "3️⃣"]
CLEAR_MARK = "🟨"


def render_grid(board: int, overlay: dict | None = None) -> str:
    """overlay: {cell_index: emoji} drawn on top of the board state."""
    overlay = overlay or {}
    lines = []
    for r in range(SIZE):
        row_chars = []
        for c in range(SIZE):
            cell = idx(r, c)
            if cell in overlay:
                row_chars.append(overlay[cell])
            elif board & (1 << cell):
                row_chars.append(CELL_FILLED)
            else:
                row_chars.append(CELL_EMPTY)
        lines.append("".join(row_chars))
    return "\n".join(lines)


def render_step(board_before: int, code: str, row: int, col: int, rows_cleared: list, cols_cleared: list, step_no: int) -> str:
    cells = get_piece(code)["cells"]
    emoji = STEP_EMOJI[step_no - 1] if step_no <= len(STEP_EMOJI) else "🔷"
    overlay = {idx(row + dr, col + dc): emoji for dr, dc in cells}
    grid = render_grid(board_before, overlay)
    clear_bits = set()
    for r in rows_cleared:
        for c in range(SIZE):
            clear_bits.add(idx(r, c))
    for c in cols_cleared:
        for r in range(SIZE):
            clear_bits.add(idx(r, c))
    if clear_bits:
        marked = dict(overlay)
        for cell in clear_bits:
            marked.setdefault(cell, CLEAR_MARK)
        grid = render_grid(board_before, marked)

    header = f"{emoji} Фигура {code} → строка {row + 1}, столбец {col + 1}"
    if rows_cleared or cols_cleared:
        parts = []
        if rows_cleared:
            parts.append("строки " + ", ".join(str(r + 1) for r in rows_cleared))
        if cols_cleared:
            parts.append("столбцы " + ", ".join(str(c + 1) for c in cols_cleared))
        header += f"\n💥 Очищены: {'; '.join(parts)}"
    return f"{header}\n{grid}"


def render_solution(board_before: int, solution) -> str:
    blocks = [render_step(board_before if i == 0 else solution.steps[i - 1].board_after, s.code, s.row, s.col, s.rows_cleared, s.cols_cleared, i + 1) for i, s in enumerate(solution.steps)]
    blocks.append(f"🏁 Итоговый счёт за раунд: {solution.total_score}")
    return "\n\n".join(blocks)


def render_piece_legend(codes: list[str]) -> str:
    lines = []
    for code in codes:
        piece = get_piece(code)
        art = "\n     ".join(
            "".join(CELL_FILLED if (r, c) in piece["cells"] else CELL_EMPTY for c in range(piece["width"]))
            for r in range(piece["height"])
        )
        lines.append(f"{code:<8} {art}")
    return "\n".join(lines)
