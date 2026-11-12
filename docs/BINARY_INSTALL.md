# GameTrainer — Desktop Binary Install

Build a one-file desktop executable (Linux / Raspberry Pi / desktop). Desktop only — not for mobile.

## Build

```bash
chmod +x build_binary.sh
./build_binary.sh
```

This creates a virtualenv, installs `numpy opencv-python pygame pandas pyinstaller`, and builds
`dist/gametrainer` — a single-file executable bundling the tracker, replay engine, viewer, and all
config/profiles.

## Run

```bash
./dist/gametrainer                              # list game profiles
./dist/gametrainer --list-devices                # find the capture card's index
./dist/gametrainer smash --device 0 --build-replay --view
./dist/gametrainer --build-replay                # replay of the latest session
./dist/gametrainer ./data/replays/replay.json    # view a data-point replay
```

The binary runs from any folder. It writes `./data/` in the folder you run it from, and
reads `./config/` there before its bundled config, so put a custom
`config/device_config.json` or `config/games/<game>.json` next to where you run it.

## Reassign the capture device per machine

The USB HDMI capture card appears as a different video index on different machines. Set it in
`config/device_config.json` (`device.index`) or override at runtime:

```bash
./dist/gametrainer config/games/console_generic.json --device 2
```

Find the index with `./dist/gametrainer --list-devices`, `v4l2-ctl --list-devices` (Linux), or whichever index OBS shows.

## Cable chain (any console)

Console dock HDMI Out → capture card HDMI In → card HDMI Out to TV (passthrough = your monitor
during play) → card USB 3 to the host device (Raspberry Pi, laptop, or desktop). Or drive
the TV from the host's HDMI with `--monitor`.

- PS5: turn off HDCP in Settings > System > HDMI.
- Nintendo Switch: docked mode only.

## Requirements (build machine)

Python 3.9+, pip, internet for `pip install`. The built binary runs standalone: no Python
install is needed on the target desktop. It must match the OS and CPU architecture it was
built on, so a binary built on a Raspberry Pi (ARM64) runs on ARM64 Linux, not on an x86
laptop. Build once per platform.

`gametrainer.spec` is committed (it is excluded from the `*.spec` ignore rule), so
`./build_binary.sh` works on a fresh clone.
