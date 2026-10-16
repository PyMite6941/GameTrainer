# GameTrainer Hardware Middleware Setup

## Overview
This setup guide provides instructions for configuring the GameTrainer system to capture console gameplay using HDMI Passthrough or Splitter Box hardware.

## Quick Installation

1. **Install Dependencies:**
   ```bash
   python install_middleware.py
   ```

2. **Connect Hardware:**
   - Console → Capture Card HDMI In
   - Capture Card → TV HDMI Out  
   - Capture Card → Computer USB 3.0

3. **Configure Settings:**
   - Edit `config/middleware_config.json`
   - Adjust Region of Interest coordinates
   - Set appropriate frame rate and resolution

4. **Run the System:**
   ```bash
   cd GameTrainer
   python main.py
   ```

## Hardware Options

### Option A: USB Capture Card with Passthrough
**Recommended:** Elgato Game Capture HD60S Pro or equivalent

### Option B: HDMI Splitter + USB Capture Stick
**Alternative:** Separate splitter and capture device

## Troubleshooting

- **No Video Detected:** Check all connections and drivers
- **Lag in Gameplay:** Use high-quality capture card
- **Video Quality Issues:** Adjust brightness/contrast in settings
- **Audio Problems:** Ensure audio cable is properly connected

## Support
For support, refer to the documentation in the `docs/` directory or contact support.
