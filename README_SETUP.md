# GameTrainer Setup

The short version. Step by step, with example output: [docs/TUTORIAL.md](docs/TUTORIAL.md).

## You need

- **A host device:** Raspberry Pi 4/5 (official power supply), laptop, or desktop with a
  **USB 3 port**, and an HDMI out if it drives the screen
- An HDMI capture card (with HDMI Out for passthrough, ideally)
- Your console and a TV

## 1. Install

```bash
python3 install_middleware.py        # --ocr for HUD text, --binary for dist/gametrainer
source .venv/bin/activate
```

This creates `.venv`, installs GameTrainer, checks the host, and runs 50 self-checks. It never
overwrites your files and never uses sudo.

## 2. Guided setup

```bash
gametrainer --setup
```

This checks the host, shows how to wire your console, finds the capture card, picks or creates
your game, and teaches it the players' colors.

## 3. Play and review

```bash
gametrainer smash --build-replay --stats --view
gametrainer smash --monitor --build-replay --stats --view   # if the host drives the TV
```

Every command: [docs/CLI.md](docs/CLI.md). How the pieces fit together: [docs/MIDDLEWARE.md](docs/MIDDLEWARE.md).
