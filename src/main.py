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

    uv run python main.py calibrate

That command prints your cursor position. Hover over each landmark it lists
and paste the (x, y) numbers into calibration.toml. Then run:

    uv run python main.py run

Failsafe: move your mouse into any screen corner to abort instantly.
------------------------------------------------------------
"""

import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path
import pyautogui
# mouse to corner = abort
pyautogui.FAILSAFE = True
# tiny gap between every PyAutoGUI call
pyautogui.PAUSE = 0.05

# CALIBRATION — pixel coordinates load from calibration.toml.
# Edit calibration.toml (not this file) to tune values for your screen.

CALIBRATION_FILE = Path(__file__).resolve().parent.parent / "calibration.toml"


# calibrate mode is the recovery path for a missing/incomplete file, so it
# must work even when calibration.toml hasn't been filled in yet.
_CALIBRATING_ONLY = len(sys.argv) > 1 and sys.argv[1] == "calibrate"


def _load_calibration() -> dict:
    if not CALIBRATION_FILE.exists():
        if _CALIBRATING_ONLY:
            return {}
        raise SystemExit(
            f"Calibration file not found: {CALIBRATION_FILE}\n"
            f"Run `uv run python main.py calibrate` to measure pixel coords, then\n"
            f"create calibration.toml with those values (see the template\n"
            f"committed in this repo)."
        )
    with CALIBRATION_FILE.open("rb") as f:
        try:
            return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise SystemExit(
                f"Could not parse {CALIBRATION_FILE}: {e}\n"
                f"Keep the [section] headers and use [x, y] for each pair."
            )


def _pair(data: dict, section: str, key: str) -> tuple[int, int]:
    if _CALIBRATING_ONLY and section not in data:
        return (0, 0)  # placeholder, calibrate mode never reads it
    try:
        value = data[section][key]
    except KeyError:
        raise SystemExit(
            f"Missing [{section}].{key} in {CALIBRATION_FILE}.\n"
            f"Add it as `{key} = [x, y]`."
        )
    if not (isinstance(value, list) and len(value) == 2):
        raise SystemExit(
            f"[{section}].{key} in {CALIBRATION_FILE} must be a list of two "
            f"numbers like `{key} = [123, 456]`, got {value!r}."
        )
    return int(value[0]), int(value[1])


_CAL = _load_calibration()

# Grid geometry — the grid coords below pair with the reference tiles
# described in calibration.toml. Don't change these without also changing
# which tiles the user is asked to hover over during calibration.
CALIB_A_GRID = (0, 3)
CALIB_A_PIXEL = _pair(_CAL, "grid", "calib_a_pixel")
CALIB_B_GRID = (7, 10)
CALIB_B_PIXEL = _pair(_CAL, "grid", "calib_b_pixel")

# UI buttons
BUTTON_6_FLIPS = _pair(_CAL, "buttons", "button_6_flips")
BUTTON_PAUSE_MENU_KEY = "escape"  # key that opens the in-game menu
BUTTON_SAVE_AND_QUIT = _pair(_CAL, "buttons", "button_save_and_quit")
BUTTON_CONTINUE_RUN = _pair(_CAL, "buttons", "button_continue_run")

# Timing (seconds)
DELAY_AFTER_FLIP_CLICK = 0.8  # tile flip animation
DELAY_AFTER_BUTTON_CLICK = 0.7
DELAY_OPENING_PAUSE_MENU = 0.7
DELAY_RELOAD_TO_EVENT = 3.0  # main-menu -> back inside event
DELAY_BEFORE_START = 1.5  # countdown before the script acts

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
    from window import ensure_game_focused
    ensure_game_focused()
    print("Make sure the game shows one of:")
    print("  * main menu with Continue button")
    print("  * Crystal Sphere choice prompt (3 vs 6 flips)")
    print("  * Crystal Sphere map view")
    print("  * in-game pause menu")
    session_dir = next_event_dir()
    print(f"Output folder for this run: {session_dir.resolve()}")
    print(f"Starting in {DELAY_BEFORE_START:.0f}s — move mouse to a corner to abort.")
    time.sleep(DELAY_BEFORE_START)

    from state import prepare_for_scout
    prepare_for_scout()

    for i, centers in enumerate(ALL_RUNS):
        do_run(i, centers, session_dir)
        # After the last run we land on the main menu and STOP.
        # User reloads manually and plays the event with full info.
        if i < len(ALL_RUNS) - 1:
            continue_run()
            # Re-entering the run drops you back at the event prompt because we never committed (no exit click).

    print("\nAll scouting runs complete.")
    print(f"Screenshots: {session_dir.resolve()}")
    from compose import compose_event
    compose_event(session_dir)
    print("You are now on the main menu. Click Continue, then play the event")
    print("for real using your screenshots as a map.")


# CALIBRATION HELPER

def calibrate() -> None:
    """Print cursor position continuously so you can read off coordinates."""
    print("Calibration mode. Press Ctrl+C to stop.")
    print(f"Open {CALIBRATION_FILE} in a text editor.")
    print("Hover over each landmark below, note (x, y), and paste the numbers")
    print("into the matching setting:")
    print("  - center of tile (col 0, row 3)   -> [grid]    calib_a_pixel")
    print("  - center of tile (col 7, row 10)  -> [grid]    calib_b_pixel")
    print("  - the '6 flips / Debt' button     -> [buttons] button_6_flips")
    print("  - 'Save & Quit' in pause menu     -> [buttons] button_save_and_quit")
    print("  - 'Continue' on main menu         -> [buttons] button_continue_run")
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
    elif mode == "compose":
        from compose import compose_event, resolve_event_dir
        arg = sys.argv[2] if len(sys.argv) > 2 else None
        compose_event(resolve_event_dir(arg))
    elif mode == "capture":
        from state import STATES, capture_reference
        if len(sys.argv) < 3 or sys.argv[2] not in STATES:
            print(f"Usage: uv run python main.py capture <{'|'.join(STATES)}>")
            sys.exit(1)
        capture_reference(sys.argv[2])
    elif mode == "detect":
        from state import STATES, detect_state
        from window import ensure_game_focused
        ensure_game_focused()
        best, scores = detect_state()
        pretty = ", ".join(f"{s}={scores[s]:.1f}" for s in STATES)
        print(f"Detected: {best}  (distances: {pretty})")
    elif mode == "focus":
        from window import ensure_game_focused
        win = ensure_game_focused()
        print(f"OK — '{win.title}' is focused.")
    else:
        print(f"Unknown mode: {mode}. Use 'calibrate', 'run', 'compose', 'capture', 'detect', or 'focus'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
