# Hardware Setup

GameTrainer needs three pieces of hardware: your console, a capture card, and a **host
device**. The host is the computer the console connects to and GameTrainer runs on: a
Raspberry Pi 4 or 5, a laptop, or a desktop. What matters is that the host has the right
ports.

## The host device

| Need | Why | Raspberry Pi 4 / 5 | Laptop / desktop |
|---|---|---|---|
| **USB 3 port** (5 Gb/s) | The capture card needs it for 1080p60 | The two **blue** ports | Blue or `SS`-marked port, or USB-C |
| **HDMI output** | Monitor mode, and watching replays | micro-HDMI: use a micro-HDMI → HDMI cable | HDMI port, or USB-C → HDMI adapter |
| **Power** | Capture cards draw power from USB | **Official supply**: Pi 4 = 5V 3A, Pi 5 = 5V 5A | Plug the laptop in while playing |
| CPU / RAM | Tracking is CPU-only, no GPU | Pi 4 or 5, 2 GB+ (4 GB recommended) | Any 64-bit CPU from the last ~8 years, 4 GB RAM |
| OS | | Raspberry Pi OS **64-bit** | Linux, Windows 10/11, macOS |

A Raspberry Pi 3 or older has only USB 2. It works with a USB 2 capture stick at
1080p30/720p60, but not with a 1080p60 card.

Check a host at any time:

```bash
gametrainer --check
```

It reports the device (for example "Raspberry Pi 4 Model B"), whether it has USB 3 ports and a
connected screen, and on a Pi whether the power supply has caused under-voltage. An
under-powered Pi is the most common reason a capture card drops out.

## What else you need

- A console: Nintendo Switch (docked), PlayStation, or Xbox
- An HDMI capture card. **With passthrough** (HDMI In + HDMI Out + USB) is best. A cheap
  USB capture stick also works with monitor mode or a splitter, see below.
- Two HDMI cables, plus a micro-HDMI → HDMI cable if the host is a Raspberry Pi and it drives
  the screen
- A TV or monitor

## Wiring: pick one of two setups

### A. Passthrough (recommended, no added lag)

```
Console ──HDMI──▶ capture card HDMI In
                  capture card HDMI Out ──HDMI──▶ TV          (you play on this)
                  capture card USB ──────USB 3──▶ host device (records the data)
```

You play on the TV exactly as without GameTrainer. The host doesn't need a screen while you
play.

```bash
gametrainer smash --build-replay --view
```

### B. Monitor mode (the host drives the screen)

```
Console ──HDMI──▶ capture card HDMI In
                  capture card USB ──USB 3──▶ host device ──HDMI──▶ TV
```

GameTrainer shows the game full screen on the host's display while it tracks. Use this when
the capture card has no HDMI Out, or you want a single cable to the TV. It adds about 1–3
frames of lag, so passthrough is better for competitive play.

```bash
gametrainer smash --monitor --build-replay --view       # Esc or q on the screen stops
```

Run it from the host's desktop: the screen plugged into its HDMI Out. `--windowed` uses a window
instead of full screen.

Print the steps for your console, with its HDCP and output settings:

```bash
gametrainer --wiring switch     # or ps5, ps4, xbox, xb1
```

## Console notes

- **PS5 / PS4:** turn HDCP off (PS5: Settings › System › HDMI › Enable HDCP), or the card gets a
  black picture. GameTrainer warns you after 3 seconds of black.
- **Nintendo Switch:** use docked mode only. Handheld mode has no HDMI out.
- **Xbox:** works as is; set the output to 1080p.
- Set every console to **1080p** output. Most cards pass 4K through but capture 1080p.

## No passthrough? Use monitor mode or a splitter

Cheap USB capture sticks have no HDMI Out. Either use monitor mode (B), or put a powered
1-in-2-out HDMI splitter in front: console → splitter, Out 1 → TV, Out 2 → capture stick → host.
Splitters don't remove HDCP. Sticks usually do 1080p30, so copy
`config/setup_examples/usb2_capture_stick_1080p30.json` to `config/device_config.json`.

## Find the capture card

```bash
gametrainer --list-devices --save   # probes indexes 0-9, saves the card's index
```

`--save` writes the index to `config/device_config.json` on this host. You can also pass
`--device N`. The index can change when you plug in other cameras; `gametrainer --check`
warns you when the card is no longer at the saved index. On Linux, `--list-devices` also shows
whether the card is on a USB 2 or USB 3 link.

Ready-made device configs are in `config/setup_examples/`: a passthrough card at 1080p60, a
USB 2 stick at 1080p30, and a lighter setting for slower hosts (older laptops, a busy Pi).

## Check it

```bash
gametrainer console_generic --seconds 10 --preview
```

A preview window shows the capture with tracked players circled, and the terminal prints one
line per tracked frame. If you get `Capture error`, check the USB cable and run
`gametrainer --list-devices --save`.

Easiest of all: `gametrainer --setup` walks through all of this step by step.
