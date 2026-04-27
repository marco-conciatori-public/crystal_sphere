"""
Game window detection and focus management.

Verifies Slay the Spire 2 is running before the scout starts and brings
its window to the foreground so PyAutoGUI clicks land in the right place.
"""

import time

import pygetwindow as gw

GAME_WINDOW_TITLE = "Slay the Spire 2"
FOCUS_WAIT = 0.5


def find_game_window(title: str = GAME_WINDOW_TITLE):
    matches = gw.getWindowsWithTitle(title)
    return matches[0] if matches else None


def ensure_game_focused(title: str = GAME_WINDOW_TITLE):
    win = find_game_window(title)
    if win is None:
        raise SystemExit(
            f"Could not find a window titled '{title}'. "
            f"Is Slay the Spire 2 running?"
        )
    if win.isActive and not win.isMinimized:
        print(f"Game window '{win.title}' is already focused.")
        return win
    print(f"Focusing game window: '{win.title}'")
    if win.isMinimized:
        win.restore()
    try:
        win.activate()
    except Exception:
        # SetForegroundWindow can be blocked on Windows; minimize+restore reliably forces focus
        win.minimize()
        time.sleep(0.1)
        win.restore()
    time.sleep(FOCUS_WAIT)
    if not win.isActive:
        raise SystemExit(
            f"Found '{win.title}' but couldn't bring it to focus. "
            f"Click on the game window manually."
        )
    return win
