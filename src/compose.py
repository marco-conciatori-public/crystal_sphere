"""
Compose the 3 scouting screenshots into a single fully-revealed map image.

Each screenshot reveals a different subset of tiles (per RUN_1/RUN_2/RUN_3
in src/main.py). For every real tile we copy its pixels from the screenshot of
the run that revealed it, pasted onto a base image (run 1) so the
surrounding UI and unrevealed corners are preserved.
"""

from pathlib import Path

from PIL import Image

from main import (
    ALL_RUNS,
    CALIB_A_GRID, CALIB_A_PIXEL,
    CALIB_B_GRID, CALIB_B_PIXEL,
    OUTPUT_DIR,
    tile_to_pixel,
)


# Circle-shaped grid mask — mirrors the ASCII map in src/main.py.
_GRID_MASK = [
    "...11111...",
    "..1111111..",
    ".111111111.",
    "11111111111",
    "11111111111",
    "11111111111",
    "11111111111",
    "11111111111",
    ".111111111.",
    "..1111111..",
    "...11111...",
]
REAL_TILES: set[tuple[int, int]] = {
    (c, r)
    for r, row in enumerate(_GRID_MASK)
    for c, ch in enumerate(row)
    if ch == "1"
}


def _tile_step() -> tuple[float, float]:
    (ca, ra), (xa, ya) = CALIB_A_GRID, CALIB_A_PIXEL
    (cb, rb), (xb, yb) = CALIB_B_GRID, CALIB_B_PIXEL
    return (xb - xa) / (cb - ca), (yb - ya) / (rb - ra)


def _tile_box(col: int, row: int, step_x: float, step_y: float) -> tuple[int, int, int, int]:
    """Pixel bounding box of one tile, snapped so neighbours tile seamlessly."""
    cx, cy = tile_to_pixel(col, row)
    left = round(cx - step_x / 2)
    top = round(cy - step_y / 2)
    right = round(cx + step_x / 2)
    bottom = round(cy + step_y / 2)
    return left, top, right, bottom


def _tile_owner() -> dict[tuple[int, int], int]:
    """Map each real tile to the index of the run (0..2) that reveals it.
    A run reveals every tile within Chebyshev distance 1 of one of its centers."""
    owner: dict[tuple[int, int], int] = {}
    for run_idx, centers in enumerate(ALL_RUNS):
        for cc, cr in centers:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    tile = (cc + dc, cr + dr)
                    if tile in REAL_TILES and tile not in owner:
                        owner[tile] = run_idx
    missing = REAL_TILES - owner.keys()
    if missing:
        raise RuntimeError(
            f"{len(missing)} real tiles are not covered by any run: "
            f"{sorted(missing)}"
        )
    return owner


def find_run_screenshots(session_dir: Path) -> list[Path]:
    """Most recent screenshot for each of the 3 runs, in order."""
    paths: list[Path] = []
    for i in range(1, len(ALL_RUNS) + 1):
        matches = sorted(session_dir.glob(f"run{i}_revealed_*.png"))
        if not matches:
            raise FileNotFoundError(f"No screenshot for run {i} in {session_dir}")
        paths.append(matches[-1])
    return paths


def latest_event_dir() -> Path:
    candidates = [
        (int(p.name[len("event_"):]), p)
        for p in OUTPUT_DIR.glob("event_*")
        if p.is_dir() and p.name[len("event_"):].isdigit()
    ]
    if not candidates:
        raise FileNotFoundError(f"No event_N folders in {OUTPUT_DIR}")
    return max(candidates)[1]


def resolve_event_dir(arg: str | None) -> Path:
    if arg is None:
        return latest_event_dir()
    if arg.isdigit():
        return OUTPUT_DIR / f"event_{arg}"
    p = Path(arg)
    return p if p.is_absolute() or p.exists() else OUTPUT_DIR / arg


def compose_event(session_dir: Path) -> Path:
    paths = find_run_screenshots(session_dir)
    images = [Image.open(p) for p in paths]
    base = images[0].copy()

    step_x, step_y = _tile_step()
    owner = _tile_owner()

    for tile, run_idx in owner.items():
        if run_idx == 0:
            continue
        col, row = tile
        box = _tile_box(col, row, step_x, step_y)
        region = images[run_idx].crop(box)
        base.paste(region, box[:2])

    out_path = session_dir / "composite_revealed.png"
    base.save(out_path)
    print(f"Composed map saved: {out_path}")
    return out_path
