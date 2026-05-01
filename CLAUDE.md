# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PyAutoGUI script that automates the **Crystal Sphere** event in *Slay the Spire 2*. It reveals every tile of the (circle-shaped) 11×11 grid by repeatedly choosing the 6-flip "Debt" option, flipping 5 tiles, screenshotting, then **Save & Quit → Continue** to reset the run without committing — across 3 such cycles (5 + 5 + 4 = 14 flips). The script stops at the main menu before the final committed play-through, after composing the 3 screenshots into one fully-revealed map.

## Commands

The project is managed with **uv** (see `uv.lock`). Python ≥3.12, <3.14.

```bash
uv sync                  # install deps into .venv
uv run python main.py calibrate         # print live cursor coords for measuring landmarks
uv run python main.py capture <state>   # capture state-detection reference (initial|choice|map|paused)
uv run python main.py detect            # detect current state and print distances (no actions taken)
uv run python main.py focus             # find Slay the Spire 2 window and bring it to the foreground
uv run python main.py run               # default — focus, detect state, full scout + auto-compose
uv run python main.py compose           # rebuild composite for the latest event_N
uv run python main.py compose 3         # rebuild composite for event_3
uv run python main.py                   # same as 'run'
```

There are no tests, lint config, or build step.

## Architecture

`main.py` is the entire program. Worth knowing:

- **Calibration values live in `calibration.toml`** at the repo root and are loaded by `main.py` at import time (`_load_calibration` / `_pair`). The exposed module constants (`CALIB_A_PIXEL`, `CALIB_B_PIXEL`, `BUTTON_*`) keep the same names so `compose.py` and `state.py` can keep importing them. These pixel values are screen-resolution-specific and must be remeasured via `calibrate` mode whenever the monitor or game window changes. `tile_to_pixel()` linearly interpolates every tile from those two reference points, so the two calibration tiles must be **far apart** and on **real (non-corner) tiles** of the circle. The reference tile *grid* coords (`CALIB_A_GRID`, `CALIB_B_GRID`) stay in `main.py` because they're a design choice, not a per-screen measurement — they pair with the tiles the user is told to hover over during calibrate. `calibrate` mode tolerates a missing `calibration.toml` (returns `(0,0)` placeholders) so it remains usable as the recovery path; other modes fail loudly with a SystemExit if the file is missing or malformed.

- **The grid is circle-shaped, not square.** The corner cells of the 11×11 array are off-map. The ASCII map in `main.py` (around the `RUN_*` constants) is the source of truth for which tiles exist. `RUN_1`/`RUN_2`/`RUN_3` are precomputed 3×3-coverage centers chosen so that their unions cover every real tile — do not edit these casually.

- **Critical safety invariant: never spend the 6th flip.** The script picks the 6-flip option each round but `MAX_FLIPS_PER_RUN = 5` enforces a hard cap in `do_run()`. The 6th flip commits event state, breaking the save-scum loop. Any change that adds clicks per run must preserve this cap.

- **Loop control flow** (`run_full_scout`): for each run, choose 6-flip option → flip 5 tiles → screenshot → Save & Quit → between runs, `Continue` from main menu re-enters the un-committed event. After the final run the script intentionally stops on the main menu and lets the user play manually.

- **Failsafe.** `pyautogui.FAILSAFE = True`: moving the mouse to any screen corner aborts immediately. Preserve this when refactoring.

- **Output.** Each `run` invocation creates a fresh `./output/event_N/` (next free integer) and drops `run{N}_revealed_{timestamp}.png` files plus a final `composite_revealed.png` there.

## Modules

- `main.py` — automation driver (PyAutoGUI clicks, calibration, scouting loop). Owns the calibration constants and `tile_to_pixel`.
- `compose.py` — image composition. Imports calibration + `ALL_RUNS` from `main.py`, computes which run reveals each real tile, and pastes the per-tile crops onto a base image. Has its own `REAL_TILES` mask mirroring the ASCII grid in `main.py` — keep the two in sync if either changes. Asserts every real tile has an owning run, so a broken `RUN_*` pattern fails loudly.
- `state.py` — pre-flight state detection. Recognizes 4 acceptable starting states (`initial`/`choice`/`map`/`paused`) by cropping a region anchored to the calibration (top-left at `CALIB_A_PIXEL`, width = 2·(xb−xa), height = (yb−ya)) and matching it to per-state references in `references/` via mean per-channel pixel distance. `prepare_for_scout()` then performs whichever transition is needed to land in `choice` before the scouting loop runs. References are calibration-coupled — recapture (`python main.py capture <state>`) after recalibration, since the region size will change.
- `window.py` — Slay the Spire 2 window detection and focus. Uses `pygetwindow` (transitive dep of pyautogui). `ensure_game_focused()` looks up `GAME_WINDOW_TITLE` ("Slay the Spire 2", substring match), restores if minimized, and brings the window to the foreground — falling back to a minimize+restore trick when Windows blocks `SetForegroundWindow`. Raises `SystemExit` with a clear message if the game isn't running or focus can't be set. Called at the start of `run` and `detect`.
- `Crystal Sphere.bat` — Windows double-click launcher meant to be copied anywhere on the user's machine. Hardcodes `PROJECT_DIR`, `pushd`s into it, runs `uv run python main.py`, then copies the latest `output/event_N/composite_revealed.png` next to the launcher (`%~dp0`). Picks the latest event folder by **numeric** suffix via a small embedded PowerShell call (not alphabetic — `event_10` must outrank `event_2`); keep that logic if `event_N` naming ever changes. Skips the copy on non-zero exit so a FAILSAFE/aborted run doesn't ship a stale image.

## Open work

`docs/TODO.txt` remaining item: automatic element recognition from the screenshots.
