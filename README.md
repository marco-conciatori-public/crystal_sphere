# Crystal Sphere

A PyAutoGUI script that automates the **Crystal Sphere** event in *Slay the Spire 2*.

It reveals every tile of the circle-shaped 11×11 grid by repeatedly picking the 6-flip
Debt" option, flipping 5 tiles, taking a screenshot, then **Save & Quit → Continue** to
reset the run without committing. Three cycles (5 + 5 + 4 = 14 flips) cover the whole map;
the screenshots are stitched into one fully-revealed composite. The script stops at the
main menu so you can play the run manually.

## Requirements

- Windows
- Python ≥ 3.12, < 3.14
- [uv](https://docs.astral.sh/uv/)
- *Slay the Spire 2* running, with the Crystal Sphere event open

## Setup

```bash
uv sync
```

Pixel coordinates are screen-resolution-specific. Calibrate before the
first run (and again whenever your monitor or game window changes):

```bash
uv run python main.py calibrate
```

Follow the on-screen prompts and write the printed values into `calibration.toml`.

## Usage

```bash
uv run python main.py           # run the full program and get the explored map's image
```

Other modes:
```bash
uv run python main.py focus      # bring the game window to the foreground
uv run python main.py detect     # detect current state without acting
uv run python main.py compose    # rebuild composite for the latest event_N
```

Output lands in `./output/event_N/` as per-run screenshots plus a final `composite_revealed.png`.

Move the cursor into any screen corner to interrupt the script.