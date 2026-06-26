"""Block Blast solving engine.

Board is an 8x8 grid represented as a 64-bit integer bitmask
(bit index = row * SIZE + col, bit set = filled cell).

Given the current board and the 3 pieces dealt this turn, `solve()`
brute-forces every ordering and every placement of the three pieces,
simulating line clears after each placement, and returns the
sequence that maximizes a score heuristic while keeping the board as
open as possible (tie-break).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations

from pieces import get_piece

SIZE = 8
FULL_MASK = (1 << (SIZE * SIZE)) - 1

ROW_MASKS = [sum(1 << (r * SIZE + c) for c in range(SIZE)) for r in range(SIZE)]
COL_MASKS = [sum(1 << (r * SIZE + c) for r in range(SIZE)) for c in range(SIZE)]


def idx(r: int, c: int) -> int:
    return r * SIZE + c


def empty_board() -> int:
    return 0


def grid_to_board(grid) -> int:
    board = 0
    for r in range(SIZE):
        for c in range(SIZE):
            if grid[r][c]:
                board |= 1 << idx(r, c)
    return board


def board_to_grid(board: int) -> list[list[int]]:
    return [[1 if board & (1 << idx(r, c)) else 0 for c in range(SIZE)] for r in range(SIZE)]


@lru_cache(maxsize=None)
def piece_placements(code: str) -> tuple[tuple[int, int, int], ...]:
    """All (row, col, mask) placements of a piece within an empty SIZE x SIZE board."""
    cells = get_piece(code)["cells"]
    h = max(r for r, _ in cells) + 1
    w = max(c for _, c in cells) + 1
    out = []
    for r0 in range(SIZE - h + 1):
        for c0 in range(SIZE - w + 1):
            mask = 0
            for dr, dc in cells:
                mask |= 1 << idx(r0 + dr, c0 + dc)
            out.append((r0, c0, mask))
    return tuple(out)


def clear_lines(board: int) -> tuple[int, list[int], list[int]]:
    rows = [r for r in range(SIZE) if board & ROW_MASKS[r] == ROW_MASKS[r]]
    cols = [c for c in range(SIZE) if board & COL_MASKS[c] == COL_MASKS[c]]
    new_board = board
    for r in rows:
        new_board &= ~ROW_MASKS[r]
    for c in cols:
        new_board &= ~COL_MASKS[c]
    return new_board & FULL_MASK, rows, cols


def place_and_clear(board: int, piece_mask: int) -> tuple[int, list[int], list[int]]:
    placed = board | piece_mask
    return clear_lines(placed)


_NEIGHBOR_MASKS = []
for _r in range(SIZE):
    for _c in range(SIZE):
        _mask = 0
        for _dr, _dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            _nr, _nc = _r + _dr, _c + _dc
            if 0 <= _nr < SIZE and 0 <= _nc < SIZE:
                _mask |= 1 << (_nr * SIZE + _nc)
        _NEIGHBOR_MASKS.append(_mask)


def board_openness(board: int) -> int:
    """Heuristic: more empty cells is better; isolated single-cell holes are bad."""
    empty_count = SIZE * SIZE - bin(board).count("1")
    isolated = 0
    for cell in range(SIZE * SIZE):
        bit = 1 << cell
        if board & bit:
            continue
        nmask = _NEIGHBOR_MASKS[cell]
        if board & nmask == nmask:  # every in-bounds neighbor is filled
            isolated += 1
    return empty_count - 3 * isolated


def openness_after_place(board_before: int, openness_before: int, piece_mask: int, piece_cell_count: int) -> int:
    """openness(board_before | piece_mask) without a full O(64) rescan.

    Only the cells of the piece and their neighbors can change isolation
    status, so this touches at most a handful of cells instead of all 64.
    Only valid when placing piece_mask does not clear any line (board_after
    is exactly board_before | piece_mask) -- the caller must fall back to a
    full board_openness() recompute on the rare line-clear branch, since a
    clear can flip up to a whole row/column at once.
    """
    board_after = board_before | piece_mask
    neighbor_masks = _NEIGHBOR_MASKS

    affected_mask = piece_mask
    rem = piece_mask
    while rem:
        low = rem & (rem - 1)
        cell = (rem ^ low).bit_length() - 1
        affected_mask |= neighbor_masks[cell]
        rem = low

    isolated_delta = 0
    rem = affected_mask
    while rem:
        low = rem & (rem - 1)
        bit = rem ^ low
        cell = bit.bit_length() - 1
        nmask = neighbor_masks[cell]
        was_isolated = not (board_before & bit) and (board_before & nmask) == nmask
        is_isolated = not (board_after & bit) and (board_after & nmask) == nmask
        if was_isolated and not is_isolated:
            isolated_delta -= 1
        elif is_isolated and not was_isolated:
            isolated_delta += 1
        rem = low

    return openness_before - piece_cell_count - 3 * isolated_delta


def score_for_move(cell_count: int, rows: list[int], cols: list[int], combo: int) -> int:
    lines = len(rows) + len(cols)
    points = cell_count
    if lines:
        points += 10 * lines + 5 * lines * lines  # bonus for multi-line clears
        points += 5 * combo  # bonus for consecutive-clearing streak
    return points


@dataclass
class Step:
    code: str
    row: int
    col: int
    cells: tuple
    rows_cleared: list
    cols_cleared: list
    score: int
    board_after: int


@dataclass
class Solution:
    steps: list  # list[Step] in the chosen placement order
    total_score: int
    final_board: int


def solve(board: int, codes: list[str]) -> Solution | None:
    """Try every ordering/placement of the 3 dealt pieces, return the best Solution.

    board_openness() is fairly expensive (O(64) cells with neighbor checks),
    so it is only evaluated for candidates whose raw score already matches
    or beats the best one found so far -- that alone cuts the call count by
    a couple orders of magnitude versus scoring every candidate.
    """
    best: Solution | None = None
    best_total = None
    best_openness = None
    openness0 = board_openness(board)

    cell_counts = {code: len(get_piece(code)["cells"]) for code in codes}

    seen_orders = set()
    for order in permutations(range(len(codes))):
        order_codes = tuple(codes[i] for i in order)
        if order_codes in seen_orders:
            continue
        seen_orders.add(order_codes)
        n0 = cell_counts[order_codes[0]]
        n1 = cell_counts[order_codes[1]]
        n2 = cell_counts[order_codes[2]]

        for r0, c0, m0 in piece_placements(order_codes[0]):
            if board & m0:
                continue
            board1, rows1, cols1 = place_and_clear(board, m0)
            cleared1 = bool(rows1 or cols1)
            combo1 = 1 if cleared1 else 0
            score1 = score_for_move(n0, rows1, cols1, combo1)
            openness1 = board_openness(board1) if cleared1 else openness_after_place(board, openness0, m0, n0)

            for r1, c1, m1 in piece_placements(order_codes[1]):
                if board1 & m1:
                    continue
                board2, rows2, cols2 = place_and_clear(board1, m1)
                cleared2 = bool(rows2 or cols2)
                combo2 = combo1 + 1 if cleared2 else 0
                score2 = score_for_move(n1, rows2, cols2, combo2)
                partial = score1 + score2
                openness2 = board_openness(board2) if cleared2 else openness_after_place(board1, openness1, m1, n1)

                for r2, c2, m2 in piece_placements(order_codes[2]):
                    if board2 & m2:
                        continue
                    board3, rows3, cols3 = place_and_clear(board2, m2)
                    cleared3 = bool(rows3 or cols3)
                    combo3 = combo2 + 1 if cleared3 else 0
                    score3 = score_for_move(n2, rows3, cols3, combo3)

                    total = partial + score3
                    if best_total is not None and total < best_total:
                        continue

                    openness = board_openness(board3) if cleared3 else openness_after_place(board2, openness2, m2, n2)
                    if (
                        best_total is None
                        or total > best_total
                        or (total == best_total and openness > best_openness)
                    ):
                        best_total = total
                        best_openness = openness
                        best = Solution(
                            steps=[
                                Step(order_codes[0], r0, c0, get_piece(order_codes[0])["cells"], rows1, cols1, score1, board1),
                                Step(order_codes[1], r1, c1, get_piece(order_codes[1])["cells"], rows2, cols2, score2, board2),
                                Step(order_codes[2], r2, c2, get_piece(order_codes[2])["cells"], rows3, cols3, score3, board3),
                            ],
                            total_score=total,
                            final_board=board3,
                        )
    return best
