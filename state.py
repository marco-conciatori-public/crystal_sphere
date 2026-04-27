"""
Pre-flight game-state detection for the Crystal Sphere scout.

The scouting loop assumes it starts at the 3-vs-6-flips choice prompt.
This module recognizes 4 acceptable starting states and brings the game
into the 'choice' state before the loop begins:

    initial  - main menu with Continue button       -> click Continue
    choice   - 3-vs-6 flips choice prompt           -> nothing to do
    map      - in-event grid view (after choosing)  -> Save & Quit, Continue
    paused   - in-game pause menu open              -> Save & Quit, Continue

Detection works by capturing one reference crop per state (`capture <state>`)
of a screen region known to differ between states, then matching the live
screenshot to the closest reference by mean per-channel pixel distance.

The detection region is anchored to the existing calibration:
top-left at CALIB_A_PIXEL, width = 2*(xb-xa), height = (yb-ya).
"""

import time
from pathlib import Path

import pyautogui
from PIL import Image, ImageChops, ImageStat

from main import (
    BUTTON_SAVE_AND_QUIT,
    CALIB_A_PIXEL, CALIB_B_PIXEL,
    DELAY_RELOAD_TO_EVENT,
    click,
    continue_run,
    save_and_quit,
)

STATES = ("initial", "choice", "map", "paused")
REFERENCES_DIR = Path("references")
CAPTURE_COUNTDOWN = 5.0
MATCH_THRESHOLD = 40.0  # max mean per-channel pixel distance for a valid match


def detection_box() -> tuple[int, int, int, int]:
    xa, ya = CALIB_A_PIXEL
    xb, yb = CALIB_B_PIXEL
    dx, dy = xb - xa, yb - ya
    return xa, ya, xa + 2 * dx, ya + dy


def capture_region() -> Image.Image:
    return pyautogui.screenshot().crop(detection_box())


def reference_path(state: str) -> Path:
    if state not in STATES:
        raise ValueError(f"Unknown state '{state}'. Valid: {STATES}")
    return REFERENCES_DIR / f"{state}.png"


def capture_reference(state: str, delay: float = CAPTURE_COUNTDOWN) -> Path:
    out = reference_path(state)
    REFERENCES_DIR.mkdir(exist_ok=True)
    print(f"Capturing reference for state '{state}'.")
    print(f"Put the game in the '{state}' state and focus the window.")
    print(f"Capturing in {delay:.0f}s...")
    time.sleep(delay)
    img = capture_region()
    img.save(out)
    print(f"Saved: {out}  ({img.size[0]}x{img.size[1]})")
    return out


def _distance(a: Image.Image, b: Image.Image) -> float:
    """Mean per-channel absolute pixel difference (0..255)."""
    diff = ImageChops.difference(a, b)
    stat = ImageStat.Stat(diff)
    return sum(stat.mean) / len(stat.mean)


def _distance_to(state: str, current: Image.Image | None = None) -> float:
    ref_path = reference_path(state)
    if not ref_path.exists():
        raise SystemExit(
            f"Missing reference image for state '{state}': {ref_path}\n"
            f"Capture it with: python main.py capture {state}"
        )
    ref = Image.open(ref_path)
    if current is None:
        current = capture_region()
    if ref.size != current.size:
        raise SystemExit(
            f"Reference '{state}' has size {ref.size} but live region is "
            f"{current.size}. Recalibration changes the region — "
            f"recapture references with: python main.py capture {state}"
        )
    return _distance(ref, current)


def detect_state() -> tuple[str, dict[str, float]]:
    missing = [s for s in STATES if not reference_path(s).exists()]
    if missing:
        raise SystemExit(
            f"Missing reference images for: {', '.join(missing)}.\n"
            f"Capture each one with:  python main.py capture <state>"
        )
    current = capture_region()
    scores = {s: _distance_to(s, current) for s in STATES}
    best = min(scores, key=lambda k: scores[k])
    if scores[best] > MATCH_THRESHOLD:
        pretty = ", ".join(f"{s}={scores[s]:.1f}" for s in STATES)
        raise SystemExit(
            f"No reference matched the current screen "
            f"(best: {best}={scores[best]:.1f}, threshold={MATCH_THRESHOLD:.0f}).\n"
            f"Distances: {pretty}\n"
            f"Recapture references with: python main.py capture <state>"
        )
    return best, scores


def prepare_for_scout() -> str:
    """Detect current game state, transition into 'choice', return the
    originally detected state."""
    state, scores = detect_state()
    pretty = ", ".join(f"{s}={scores[s]:.1f}" for s in STATES)
    print(f"Detected state: {state}  (distances: {pretty})")
    if state == "initial":
        continue_run()
    elif state == "choice":
        pass
    elif state == "map":
        save_and_quit()
        continue_run()
    elif state == "paused":
        click(BUTTON_SAVE_AND_QUIT)
        time.sleep(DELAY_RELOAD_TO_EVENT)
        continue_run()
    distance = _distance_to("choice")
    print(f"Post-transition distance to 'choice': {distance:.1f}")
    if distance > MATCH_THRESHOLD:
        raise SystemExit(
            f"Expected the Crystal Sphere choice prompt after transitioning "
            f"from '{state}', but the screen didn't match "
            f"(distance={distance:.1f}, threshold={MATCH_THRESHOLD:.0f}).\n"
            f"This script only works for the Crystal Sphere event."
        )
    return state
