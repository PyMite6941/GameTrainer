# Hardware Setup

## What you need

- A console: Nintendo Switch (docked), PlayStation, or Xbox
- An HDMI capture card with **passthrough** (HDMI In + HDMI Out + USB)
- Two HDMI cables
- A USB 3.0 port on the laptop or desktop (no GPU needed)
- A TV or monitor

## Cable chain

1. Console (or Switch dock) **HDMI Out** → capture card **HDMI In**
2. Capture card **HDMI Out** → TV. This is passthrough: it adds no lag, and the TV is your
   monitor while you play.
3. Capture card **USB** → laptop USB 3.0 port

The card shows up as a standard UVC video device, so most cards need no driver on Linux.

## Console notes

- **PS5:** turn HDCP off (Settings › System › HDMI › Enable HDCP), or the card gets a black
  picture.
- **Nintendo Switch:** use docked mode only. Handheld mode has no HDMI out.
- **Xbox:** works as is over HDMI.

Print these steps for your console, with its HDCP and output settings:

```bash
gametrainer --wiring switch     # or ps5, ps4, xbox, xb1
```

## No passthrough? Use a splitter

Cheap USB capture sticks have no HDMI Out. Put a powered 1-in-2-out HDMI splitter in front:
console → splitter, Out 1 → TV, Out 2 → capture stick → laptop. Splitters don't remove HDCP.
Sticks usually do 1080p30, so copy `config/setup_examples/usb2_capture_stick_1080p30.json`
to `config/device_config.json`.

## USB 3 matters

1080p60 needs a USB 3 port: blue, or marked SS. On a USB 2 port most cards silently drop to
a lower mode. `gametrainer --list-devices` and `gametrainer --check` show the link speed on Linux.

## Find the capture device

```bash
gametrainer --list-devices --save   # probes indexes 0-9, saves the capture card's index
v4l2-ctl --list-devices        # Linux alternative: note the /dev/videoN index of the card
```

`--save` writes the index to `config/device_config.json`. You can also pass `--device N`.
The index can change when you plug in other cameras, so check it again on each new machine.
`gametrainer --check` warns you when the card is no longer at the saved index.

Ready-made device configs are in `config/setup_examples/`: a passthrough card at 1080p60, a
USB 2 stick at 1080p30, and a lighter setting for slow laptops.

## Check it

```bash
gametrainer console_generic --device 0 --seconds 10 --preview
```

A preview window shows the capture with tracked players circled, and the terminal prints
one line per tracked frame. If you get `Capture error`, check the USB cable and
the device index.
