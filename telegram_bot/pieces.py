"""Piece shape library for the Block Blast solver.

A piece is a tuple of (row, col) offsets, normalized so the minimum
row and column are both 0. New shapes can be added to BASE_SHAPES;
all of their unique 90-degree rotations are generated automatically
and exposed as separate selectable pieces (since Block Blast hands
you pieces in a fixed orientation, not a shape "family").
"""

from __future__ import annotations

Cells = tuple[tuple[int, int], ...]


def normalize(cells) -> Cells:
    cells = list(cells)
    min_r = min(r for r, _ in cells)
    min_c = min(c for _, c in cells)
    return tuple(sorted((r - min_r, c - min_c) for r, c in cells))


def rotate90(cells) -> Cells:
    # (r, c) -> (c, -r), then normalize
    return normalize((c, -r) for r, c in cells)


def unique_rotations(cells) -> list[Cells]:
    base = normalize(cells)
    seen = []
    cur = base
    for _ in range(4):
        if cur not in seen:
            seen.append(cur)
        cur = rotate90(cur)
    return seen


def bounding_box(cells) -> tuple[int, int]:
    return (max(r for r, _ in cells) + 1, max(c for _, c in cells) + 1)


# Base shapes. Keys double as the human-readable shape family name.
BASE_SHAPES: dict[str, Cells] = {
    "I1": ((0, 0),),
    "I2": ((0, 0), (0, 1)),
    "I3": ((0, 0), (0, 1), (0, 2)),
    "I4": ((0, 0), (0, 1), (0, 2), (0, 3)),
    "I5": ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4)),
    "SQ2": ((0, 0), (0, 1), (1, 0), (1, 1)),
    "SQ3": (
        (0, 0), (0, 1), (0, 2),
        (1, 0), (1, 1), (1, 2),
        (2, 0), (2, 1), (2, 2),
    ),
    "R23": ((0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)),
    "L": ((0, 0), (1, 0), (2, 0), (2, 1)),
    "J": ((0, 1), (1, 1), (2, 1), (2, 0)),
    "T": ((0, 0), (0, 1), (0, 2), (1, 1)),
    "S": ((0, 1), (0, 2), (1, 0), (1, 1)),
    "Z": ((0, 0), (0, 1), (1, 1), (1, 2)),
    "P": ((0, 1), (1, 0), (1, 1), (1, 2), (2, 1)),
    "U": ((0, 0), (0, 2), (1, 0), (1, 1), (1, 2)),
    "CORNER": ((0, 0), (0, 1), (0, 2), (1, 0), (2, 0)),
}


def _build_pieces() -> list[dict]:
    pieces = []
    for family, base in BASE_SHAPES.items():
        rotations = unique_rotations(base)
        single = len(rotations) == 1
        for i, cells in enumerate(rotations, start=1):
            h, w = bounding_box(cells)
            if single:
                code = family
            elif family.startswith("I"):
                code = f"{family}{'h' if h == 1 else 'v'}"
            else:
                code = f"{family}{i}"
            pieces.append({
                "code": code,
                "family": family,
                "cells": cells,
                "height": h,
                "width": w,
            })
    return pieces


PIECES: list[dict] = _build_pieces()
PIECES_BY_CODE: dict[str, dict] = {p["code"]: p for p in PIECES}


def get_piece(code: str) -> dict:
    return PIECES_BY_CODE[code]


def render_piece_ascii(cells, filled="⬛", empty="⬜") -> str:
    h, w = bounding_box(cells)
    grid = [[empty] * w for _ in range(h)]
    for r, c in cells:
        grid[r][c] = filled
    return "\n".join("".join(row) for row in grid)
