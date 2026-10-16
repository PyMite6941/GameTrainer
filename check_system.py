#!/usr/bin/env python3

# Check if the system is properly configured for GameTrainer middleware.

# Import middleware components
from middleware.capture.hdmi_capture import HDMI_Capture
from middleware.capture.usb_capture import USB_Capture
from middleware.analysis.frame_processor import Frame_Processor

def main():
    print("🔍 Checking GameTrainer middleware system...")

    # Check hardware
    print("\n1. Hardware Check:")
    # Check HDMI capture
    hdmi_capture = HDMI_Capture()
    if hdmi_capture.is_supported():
        print("   ✅ HDMI capture supported")
    else:
        print("   ❌ HDMI capture not supported")

    # Check USB capture
    usb_capture = USB_Capture()
    if usb_capture.is_connected():
        print("   ✅ USB capture connected")
    else:
        print("   ❌ USB capture not connected")

    # Check frame processor
    frame_processor = Frame_Processor()
    if frame_processor.is_configured():
        print("   ✅ Frame processor configured")
    else:
        print("   ❌ Frame processor not configured")

    print("\n2. Configuration Check:")

    # Check config file
    import json
    try:
        with open('config/middleware_config.json', 'r') as f:
            config = json.load(f)

        print("   ✅ Configuration file exists")
        print(f"   • Resolution: {config['hardware']['resolution']}")
        print(f"   • Frame rate: {config['hardware']['frame_rate']} FPS")

    except Exception as e:
        print(f"   ❌ Configuration file error: {e}")

    print("\n3. Console Support Check:")

    # Check console support
    try:
        with open('config/middleware_config.json', 'r') as f:
            config = json.load(f)

        consoles = config['console_support']
        for console, supported in consoles.items():
            status = "✅" if supported else "❌"
            print(f"   {status} {console.replace('_', ' ').title()}: {'Supported' if supported else 'Not Supported'}")

    except Exception as e:
        print(f"   ❌ Console support check error: {e}")

    print("\n✅ System check completed")

if __name__ == "__main__":
    main()
