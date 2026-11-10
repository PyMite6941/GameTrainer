# GameTrainer Middleware Setup

The short version. Full guides are in [`docs/`](docs/index.md).

## 1. Install

```bash
python3 install_middleware.py        # --ocr for HUD text, --binary for dist/gametrainer
source .venv/bin/activate
```

This creates `.venv`, installs GameTrainer, runs `gametrainer --check`, and runs the 42-check
verification. It never overwrites your files and never uses sudo.

## 2. Connect the hardware

```bash
gametrainer --wiring switch          # or ps5, ps4, xbox
```

Console HDMI Out → capture card HDMI In → card HDMI Out → TV. Card USB → laptop USB 3 port.
PS4/PS5: turn HDCP off. Switch: docked only. No passthrough on your device? The same command
also describes the splitter setup.

## 3. Point GameTrainer at the card

```bash
gametrainer --list-devices --save    # finds the card and saves its index
gametrainer --check                  # USB 3? right index? best capture mode?
```

Ready-made device configs (passthrough card, USB 2 stick, slow laptop) are in
`config/setup_examples/`.

## 4. Tune the game profile

```bash
gametrainer smash --calibrate        # click each player, paste color_bgr into the profile
```

## 5. Play and review

```bash
gametrainer smash --build-replay --stats --view
```

See [`docs/MIDDLEWARE.md`](docs/MIDDLEWARE.md) for how the pieces fit together and
[`docs/CLI.md`](docs/CLI.md) for every option.
