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

Open a terminal in the project's main folder and type:
```bash
uv sync
```
This creates the virtual environment needed.

Pixel coordinates are screen-resolution-specific. Calibrate before the
first run (and again whenever your monitor or game window changes):

```bash
uv run python src/main.py calibrate
```

Follow the on-screen prompts and write the printed values into `calibration.toml`. For detailed,
visual instructions see [docs/Calibration_details.pptx](docs/Calibration_details.pptx).

## Usage

```bash
uv run python src/main.py           # run the full program and get the explored map's image
```

Other modes:
```bash
uv run python src/main.py focus      # bring the game window to the foreground
uv run python src/main.py detect     # detect current state without acting
uv run python src/main.py compose    # rebuild composite for the latest event_N
```

Output lands in `./output/event_N/` as per-run screenshots plus a final `composite_revealed.png`.

## Launcher (optional)

`Crystal Sphere.bat` is a Windows double-click launcher. Copy it anywhere you like (Desktop, a notes folder, etc.).
When clicked it runs the full program and copies the `composite_revealed.png` into the launcher's own folder
(overwriting any previous copy, but originals stay in `output/event_N/`).

To use it, edit the `PROJECT_DIR` line at the top of the `.bat` with the path to the project.

## Standalone executable

To build a single-file Windows .exe (no Python install required to run):

```bash
uv sync --group dev
uv run pyinstaller crystal_sphere.spec --noconfirm
```

The result is `dist/CrystalSphere.exe`. It looks for `calibration.toml` next to itself and writes `output/` next to itself. Reference images for state detection are bundled into the .exe but can be overridden by recapturing them — recaptures land in `<exe folder>/assets/references/` and take precedence over the bundled defaults. Calibrate first with `CrystalSphere.exe calibrate`, then recapture references with `CrystalSphere.exe capture <state>` for each of `initial`, `choice`, `map`, `paused`.