# Installation

There are two ways to install: build the one-file desktop binary, or run from source.

## Option A: desktop binary (recommended for sharing)

```bash
git clone https://github.com/PyMite6941/GameTrainer.git
cd GameTrainer
chmod +x build_binary.sh
./build_binary.sh            # creates .venv, installs deps + PyInstaller, builds dist/gametrainer
./dist/gametrainer           # lists game profiles
```

Copy `dist/gametrainer` to any desktop with the same OS and CPU architecture. It runs without
Python installed. See [Desktop binary](BINARY_INSTALL.md) for details.

## Option B: the installer (from source)

Requires Python 3.9+.

```bash
git clone https://github.com/PyMite6941/GameTrainer.git
cd GameTrainer
python3 install_middleware.py          # add --ocr for HUD text, --binary to also build the binary
source .venv/bin/activate              # Windows: .venv\Scripts\activate
```

The installer:
- creates `.venv` and installs GameTrainer into it (with the `gametrainer` command)
- creates `data/`, and `config/device_config.json` if it's missing
- runs the system check
- if a capture card is connected, offers to save its index
- runs the 50-check verification

Then run `gametrainer --setup` for the guided setup, or follow the [Tutorial](TUTORIAL.md).

It never overwrites existing files and never runs `sudo`. If something needs admin rights,
such as joining the `video` group or `apt install v4l-utils tesseract-ocr`, it prints the
command for you to run. Options: `--ocr`, `--binary`, `--yes` (save the card index without
asking), `--skip-verify`, `--no-venv`.

To do it by hand instead: `python3 -m venv .venv && source .venv/bin/activate && pip install .`
(or `pip install .[ocr]`).

## Next steps

1. Connect the hardware: see [Hardware setup](HARDWARE_SETUP.md).
2. Set the device index and pick a game profile: see [Software setup](SOFTWARE_SETUP.md).
3. Track, build the replay, and view it: see the [Command reference](CLI.md).

## Troubleshooting

- **Start here**: `gametrainer --check` diagnoses most problems.
- **`Capture error`**: the card isn't at that index. Run `gametrainer --list-devices --save`.
- **Permission denied opening the card (Linux)**: `sudo usermod -aG video $USER`, then log
  out and back in.
- **Capture is 640x480 or choppy**: the card didn't accept MJPG 1080p. Try
  `"fourcc": ""` or `"fps": 30` in `config/device_config.json`.
- **A player isn't detected**: run `gametrainer <game> --calibrate`, click the player, and
  paste the printed `color_bgr` into the profile. Run with `--preview` to see what is tracked.
- **"capture card delivers 1280x720, not 1920x1080"**: set the console's output to 1080p, or
  copy a matching example from `config/setup_examples/`.
- **Black picture from a PS5**: turn HDCP off.
- **No picture from a Switch**: put it in the dock.
- **High CPU use**: raise `process_every_n_frames` or lower `detect_scale` in
  `config/device_config.json`.

`main.py` is the original demo system. Use `gametrainer` (`track_game.py`) instead.
