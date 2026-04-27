"""
Crystal Sphere Auto-Scout — Slay the Spire 2

Automates the "save & quit" scouting loop for the Crystal Sphere event:
  1. Picks the 6-flip option (gives headroom, only USE 5)
  2. Reveals tiles per run using a precomputed coverage pattern
  3. Screenshots the grid
  4. Save & Quit -> Continue, repeat until the whole circle is mapped (3 runs)
  5. Stops BEFORE the final play-through so you can do that yourself

The grid is circle-shaped (not a full square): of the 11x11 cells only the
inner 97 are real tiles. Corners are not part of the map. Across 3 rounds
we use 5 + 5 + 4 = 14 clicks to reveal every real tile.

You then look at the screenshots and play the event for real with full info.

------------------------------------------------------------
USAGE
------------------------------------------------------------
First time only — calibrate coordinates for your monitor:

    python main.py calibrate

That command prints your cursor position every 0.5s. Hover over each landmark
listed in the CONFIG section below and write its (x, y) into this file. Then run:

    python main.py run

Failsafe: move your mouse into any screen corner to abort instantly.
------------------------------------------------------------
"""

import sys
import time
from datetime import datetime
from pathlib import Path
import pyautogui
# mouse to corner = abort
pyautogui.FAILSAFE = True
# tiny gap between every PyAutoGUI call
pyautogui.PAUSE = 0.05

# CONFIG — CALIBRATE THESE FOR YOUR SCREEN

# Grid geometry
# Two real tiles used for calibration — corners are off-map so pick visible ones.
# CALIB_A: left-most tile on row 3  (col 0, row 3)
# CALIB_B: bottom-most tile on row 10 (col 7, row 10)
# Hover over each tile center in calibration mode and paste the pixel coords here.
CALIB_A_GRID = (0, 3)
CALIB_A_PIXEL = (470, 520)   # measure with: python main.py calibrate

CALIB_B_GRID = (7, 10)
CALIB_B_PIXEL = (885, 935)  # measure with: python main.py calibrate

# UI buttons
BUTTON_6_FLIPS = (1250, 750)  # "Take Debt for 6 Divines" option
BUTTON_PAUSE_MENU_KEY = "escape"  # key that opens the in-game menu
BUTTON_SAVE_AND_QUIT = (960, 730)  # "Save & Quit" in the pause menu
BUTTON_CONTINUE_RUN = (780, 685)  # "Continue" on the main menu

# Timing (seconds)
DELAY_AFTER_FLIP_CLICK = 0.9  # tile flip animation
DELAY_AFTER_BUTTON_CLICK = 0.7
DELAY_OPENING_PAUSE_MENU = 1.2
DELAY_RELOAD_TO_EVENT = 6.0  # main-menu -> back inside event
DELAY_BEFORE_START = 5.0  # countdown before the script acts

# Output
OUTPUT_DIR = Path("output")

# FLIP PATTERN — covers the full circle in 3 runs (5 + 5 + 4 = 14 clicks)
#
# Each Divine reveals a 3x3 centered on the clicked tile. The grid is
# circle-shaped: corners marked '0' below are not part of the map.
#
#     col:  0 1 2 3 4 5 6 7 8 9 10
#   row 0:  . . . 1 1 1 1 1 . . .
#   row 1:  . . 1 1 1 1 1 1 1 . .
#   row 2:  . 1 1 1 1 1 1 1 1 1 .
#   row 3:  1 1 1 1 1 1 1 1 1 1 1
#   row 4:  1 1 1 1 1 1 1 1 1 1 1
#   row 5:  1 1 1 1 1 1 1 1 1 1 1
#   row 6:  1 1 1 1 1 1 1 1 1 1 1
#   row 7:  1 1 1 1 1 1 1 1 1 1 1
#   row 8:  . 1 1 1 1 1 1 1 1 1 .
#   row 9:  . . 1 1 1 1 1 1 1 . .
#   row 10: . . . 1 1 1 1 1 . . .
#
# Coordinates below are (col, row) with (0, 0) at the top-left.
# We pick the 6-flip option each round but stop at 5

RUN_1 = [(1, 2), (1, 5), (1, 8), (4, 9), (7, 9)]  # 5 flips
RUN_2 = [(4, 1), (4, 4), (4, 6), (7, 6), (9, 7)]  # 5 flips
RUN_3 = [(7, 1), (7, 3), (9, 2), (9, 4)]  # 4 flips

ALL_RUNS = [RUN_1, RUN_2, RUN_3]

MAX_FLIPS_PER_RUN = 5  # safety cap — never use the final 6th flip

# GEOMETRY HELPERS

GRID_SIZE = 11


def tile_to_pixel(col: int, row: int) -> tuple[int, int]:
    """Map a (col, row) grid coordinate to a screen pixel."""
    (ca, ra), (xa, ya) = CALIB_A_GRID, CALIB_A_PIXEL
    (cb, rb), (xb, yb) = CALIB_B_GRID, CALIB_B_PIXEL
    step_x = (xb - xa) / (cb - ca)
    step_y = (yb - ya) / (rb - ra)
    x = xa + step_x * (col - ca)
    y = ya + step_y * (row - ra)
    return int(round(x)), int(round(y))


# ACTIONS

def click(xy: tuple[int, int], pause: float = DELAY_AFTER_BUTTON_CLICK) -> None:
    pyautogui.moveTo(xy[0], xy[1], duration=0.15)
    pyautogui.click()
    time.sleep(pause)


def flip_tile(col: int, row: int) -> None:
    px = tile_to_pixel(col, row)
    print(f"\tflip ({col:>2}, {row:>2}) -> pixel {px}")
    click(px, pause=DELAY_AFTER_FLIP_CLICK)


def next_event_dir() -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    used = {
        int(p.name[len("event_"):])
        for p in OUTPUT_DIR.glob("event_*")
        if p.is_dir() and p.name[len("event_"):].isdigit()
    }
    n = max(used, default=0) + 1
    path = OUTPUT_DIR / f"event_{n}"
    path.mkdir()
    return path


def screenshot(session_dir: Path, label: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = session_dir / f"{label}_{ts}.png"
    pyautogui.screenshot(str(path))
    print(f"\tsaved screenshot: {path}")
    return path


def save_and_quit() -> None:
    print("  -> opening pause menu")
    pyautogui.press(BUTTON_PAUSE_MENU_KEY)
    time.sleep(DELAY_OPENING_PAUSE_MENU)
    print("  -> Save & Quit")
    click(BUTTON_SAVE_AND_QUIT)
    time.sleep(DELAY_RELOAD_TO_EVENT)


def continue_run() -> None:
    print("  -> Continue from main menu")
    click(BUTTON_CONTINUE_RUN)
    time.sleep(DELAY_RELOAD_TO_EVENT)


def choose_6_flips() -> None:
    print("  -> picking the 6-flip (Debt) option")
    click(BUTTON_6_FLIPS)


# MAIN LOOP

def do_run(run_index: int, centers: list[tuple[int, int]], session_dir: Path) -> None:
    if len(centers) > MAX_FLIPS_PER_RUN:
        raise ValueError(
            f"Run {run_index + 1} has {len(centers)} flips — "
            f"refusing to exceed the {MAX_FLIPS_PER_RUN}-flip safety cap. "
            f"Spending the 6th flip can commit event state."
        )
    print(f"\n=== Scouting run {run_index + 1} / {len(ALL_RUNS)} "
          f"({len(centers)} flips) ===")
    choose_6_flips()
    for col, row in centers:
        flip_tile(col, row)
    screenshot(session_dir, f"run{run_index + 1}_revealed")
    save_and_quit()


def run_full_scout() -> None:
    print("Crystal Sphere Auto-Scout")
    print("-" * 50)
    print("Make sure:")
    print("  * The Crystal Sphere choice prompt is on screen")
    print("\t(the one offering 3-flip Gold vs 6-flip Debt)")
    print("  * Game window is focused")
    session_dir = next_event_dir()
    print(f"Output folder for this run: {session_dir.resolve()}")
    print(f"Starting in {DELAY_BEFORE_START:.0f}s — move mouse to a corner to abort.")
    time.sleep(DELAY_BEFORE_START)

    for i, centers in enumerate(ALL_RUNS):
        do_run(i, centers, session_dir)
        # After the last run we land on the main menu and STOP.
        # User reloads manually and plays the event with full info.
        if i < len(ALL_RUNS) - 1:
            continue_run()
            # Re-entering the run drops you back at the event prompt because we never committed (no exit click).

    print("\nAll scouting runs complete.")
    print(f"Screenshots: {session_dir.resolve()}")
    print("You are now on the main menu. Click Continue, then play the event")
    print("for real using your screenshots as a map.")


# CALIBRATION HELPER

def calibrate() -> None:
    """Print cursor position continuously so you can read off coordinates."""
    print("Calibration mode. Press Ctrl+C to stop.")
    print("Hover over each landmark and note (x, y):")
    print("  - center of tile (col 0, row 3)   -> CALIB_A_PIXEL")
    print("  - center of tile (col 7, row 10)  -> CALIB_B_PIXEL")
    print("  - the '6 flips / Debt' button     -> BUTTON_6_FLIPS")
    print("  - 'Save & Quit' in pause menu  -> BUTTON_SAVE_AND_QUIT")
    print("  - 'Continue' on main menu      -> BUTTON_CONTINUE_RUN")
    print()
    try:
        while True:
            x, y = pyautogui.position()
            print(f"  cursor: ({x:>5}, {y:>5})", end="\r", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nCalibration stopped.")


# ENTRY POINT

def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "calibrate":
        calibrate()
    elif mode == "run":
        run_full_scout()
    else:
        print(f"Unknown mode: {mode}. Use 'calibrate' or 'run'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
