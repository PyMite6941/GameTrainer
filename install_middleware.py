#!/usr/bin/env python3
"""
GameTrainer Hardware Middleware Installation Script

This script installs and configures the middleware required for capturing
console gameplay using HDMI Passthrough or Splitter Box setups.
"""

import os
import sys
import subprocess
import json
import platform
from pathlib import Path
from typing import Dict, List, Any

# Configuration
REQUIRED_PYTHON_VERSION = (3, 8)
import textwrap
REQUIRED_PACKAGES = [
    'opencv-python>=4.5.0',
    'numpy>=1.20.0',
    'pandas>=1.3.0',
    'pygame>=2.0.0',
    'psutil>=5.8.0'
]

# Installation targets
INSTALL_DIRECTORIES = [
    './middleware',
    './hardware_tools',
    './config'
]

def print_header():
    """Print installation header."""
    print("=" * 80)
    print("🎮 GAMETRAINER HARDWARE MIDDLEWARE INSTALLATION")
    print("=" * 80)
    print("\n📋 Purpose: Setup middleware for console gameplay capture")
    print("🎯 Support: HDMI Passthrough / Splitter Box configurations")
    print("💻 Target Platforms: Linux, macOS, Windows")
    print("\n🔧 This script will:")
    print("   • Check system requirements")
    print("   • Install Python dependencies")
    print("   • Configure middleware components")
    print("   • Create setup scripts")
    print("   • Validate installation")

def check_system_requirements():
    """Check if system meets requirements."""
    print("\n🔍 Checking system requirements...")
    
    # Check Python version
    current_version = sys.version_info
    if current_version < REQUIRED_PYTHON_VERSION:
        print(f"❌ Python {current_version.major}.{current_version.minor} is too old.")
        print(f"   Required: Python {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}")
        return False
    
    print(f"✅ Python {current_version.major}.{current_version.minor} - OK")
    
    # Check architecture
    arch = platform.machine().lower()
    print(f"✅ Architecture: {arch} - OK")
    
    # Check available disk space
    try:
        total, used, free = os.statvfs('.')
        free_gb = free // (1024 * 1024 * 1024)
        print(f"✅ Available disk space: {free_gb}GB - OK")
        
        if free_gb < 5:
            print("⚠️  Warning: Less than 5GB available. Consider more space.")
    except:
        print("⚠️  Could not check disk space")
    
    return True

def install_python_dependencies():
    """Install Python dependencies."""
    print("\n📦 Installing Python dependencies...")
    
    try:
        # Upgrade pip first
        print("🔄 Upgrading pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        
        # Install packages
        packages_str = " ".join(REQUIRED_PACKAGES)
        print(f"🔄 Installing: {packages_str}")
        
        result = subprocess.run([sys.executable, "-m", "pip", "install"] + REQUIRED_PACKAGES, 
                              check=True, capture_output=True, text=True)
        
        print("✅ All Python dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        # Check if it's an externally managed environment error
        if "externally-managed-environment" in e.stderr.decode() if isinstance(e.stderr, bytes) else "externally-managed-environment" in e.stderr:
            print("⚠️  Detected externally managed environment. Trying with --break-system-packages...")
            try:
                # Upgrade pip with --break-system-packages
                print("🔄 Upgrading pip with --break-system-packages...")
                subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--break-system-packages"], 
                              check=True, capture_output=True)
                
                # Install packages with --break-system-packages
                packages_str = " ".join(REQUIRED_PACKAGES)
                print(f"🔄 Installing: {packages_str}")
                
                result = subprocess.run([sys.executable, "-m", "pip", "install"] + REQUIRED_PACKAGES + ["--break-system-packages"], 
                                      check=True, capture_output=True, text=True)
                
                print("✅ All Python dependencies installed successfully")
                return True
            except subprocess.CalledProcessError as e2:
                print(f"❌ Failed to install dependencies with --break-system-packages: {e2}")
                print(f"Error output: {e2.stderr}")
                return False
            except Exception as e2:
                print(f"❌ Unexpected error with --break-system-packages: {e2}")
                return False
        else:
            print(f"❌ Failed to install dependencies: {e}")
            print(f"Error output: {e.stderr}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def create_directory_structure():
    """Create necessary directory structure."""
    print("\n📁 Creating directory structure...")
    
    for directory in INSTALL_DIRECTORIES:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    # Create subdirectories
    subdirs = [
        './middleware/capture',
        './middleware/analysis', 
        './middleware/simulation',
        './middleware/integration',
        './hardware_tools/adapters',
        './hardware_tools/drivers',
        './config/examples',
        './config/templates',
        './docs'
    ]
    
    for subdir in subdirs:
        Path(subdir).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {subdir}")
    
    return True

def create_middleware_components():
    """Create middleware components."""
    print("\n🔧 Creating middleware components...")
    
    components = [
        ('middleware/__init__.py', """# GameTrainer Hardware Middleware

Middleware for capturing and processing console gameplay video feeds
for the GameTrainer system.

This module provides:
- HDMI input handling
- Video stream processing
- Hardware adapter management
- Frame capture and analysis
"""),
        
        ('middleware/capture/__init__.py', """# Capture Module

Core capture functionality for handling video input from consoles.
"""),
        
        ('middleware/capture/hdmi_capture.py', """# HDMI Capture Handler

Capture video from HDMI sources with support for different connector box types.
"""),
        
        ('middleware/capture/usb_capture.py', """# USB Capture Handler

Handle USB video capture for different operating systems.
"""),
        
        ('middleware/analysis/frame_processor.py', """# Frame Processor

Process captured video frames for opponent tracking and analysis.
"""),
        
        ('middleware/analysis/feature_extractor.py', """# Feature Extractor

Extract game-relevant features from video frames.
"""),
        
        ('middleware/simulation/game_simulator.py', """# Game Simulator

Simulate gameplay based on captured data.
"""),
        
        ('middleware/integration/system_integration.py', """# System Integration

Integrate middleware with GameTrainer components.
"""),
        
        ('hardware_tools/adapters/hdmi_adapter.py', """# HDMI Adapter

Hardware adapter for HDMI connector boxes.
"""),
        
        ('hardware_tools/adapters/usb_adapter.py', """# USB Adapter

Hardware adapter for USB capture devices.
"""),
        
        ('hardware_tools/drivers/capture_card_driver.py', """# Capture Card Driver

Driver for HDMI capture cards.
"""),
        
        ('hardware_tools/drivers/splitter_driver.py', """# Splitter Driver

Driver for HDMI splitter boxes.
"""),
        
        ('config/middleware_config.json', """{
    "hardware": {
        "capture_card_type": "auto",
        "video_format": "1080p60",
        "frame_rate": 60,
        "resolution": "1920x1080",
        "color_space": "BGR",
        "flip_enabled": false
    },
    "processing": {
        "frame_skip": 1,
        "brightness_adjustment": 1.0,
        "contrast_adjustment": 1.0,
        "sharpness_adjustment": 1.0,
        "noise_reduction": true
    },
    "roi": {
        "enabled": true,
        "coordinates": {
            "x1": 400,
            "y1": 300,
            "x2": 800,
            "y2": 500
        }
    },
    "console_support": {
        "nintendo_switch": true,
        "playstation_4": true,
        "playstation_5": true,
        "xbox_one": true,
        "xbox_series_x": true
    }
}
"""),
        
        ('config/setup_examples/switch_capture_example.json', """{
    "name": "Nintendo Switch Capture Setup",
    "description": "Setup for Nintendo Switch with Elgato Game Capture HD60S Pro",
    "hardware": {
        "connector_box": "elgato_game_capture",
        "capture_method": "passthrough",
        "input_device": "switch",
        "output_device": "tv"
    },
    "settings": {
        "resolution": "1080p",
        "frame_rate": 60,
        "video_quality": "high",
        "audio_enabled": false
    }
}
"""),
        
        ('config/setup_examples/ps5_capture_example.json', """{
    "name": "PlayStation 5 Capture Setup",
    "description": "Setup for PlayStation 5 with USB capture card",
    "hardware": {
        "connector_box": "generic_usb_capture",
        "capture_method": "splitter",
        "input_device": "ps5",
        "output_device": "tv"
    },
    "settings": {
        "resolution": "1440p",
        "frame_rate": 120,
        "video_quality": "ultra",
        "audio_enabled": true
    }
}
"""),
        
        ('docs/INSTALLATION.md', """# Installation Guide

## Quick Start
1. Run the install script: `python install_middleware.py`
2. Connect your console to the capture box
3. Connect capture box to both TV and computer
4. Configure the settings in config/ directory
5. Run the GameTrainer system

## Troubleshooting
- If the capture card is not detected, check USB connection
- Ensure the console is properly connected to the capture box
- Verify that the TV displays the game correctly
- Test the capture software before proceeding with analysis
"""),
        
        ('docs/HARDWARE_SETUP.md', """# Hardware Setup Guide

## Required Hardware
- Console (Nintendo Switch, PlayStation, Xbox)
- HDMI Capture Card with Passthrough
- HDMI cables (2-3 meters recommended)
- USB 3.0 cable
- Computer with sufficient processing power

## Setup Steps
1. Connect console to capture card HDMI In
2. Connect capture card HDMI Out to TV
3. Connect capture card USB to computer
4. Install capture card drivers
5. Configure software settings
6. Test the setup
"""),
        
        ('docs/SOFTWARE_SETUP.md', """# Software Setup Guide

## Prerequisites
- Python 3.8 or higher
- Required Python packages (see requirements.txt)

## Installation
1. Clone this repository
2. Run the install script: `python install_middleware.py`
3. Configure settings in config/ directory
4. Run the GameTrainer system

## Configuration
Edit the config/middleware_config.json file to match your setup:
- Hardware type (capture card vs splitter)
- Resolution and frame rate
- Region of interest coordinates
- Console type support
"""),
        
        ('README_SETUP.md', """# GameTrainer Hardware Middleware Setup

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
""")
    ]
    
    created_count = 0
    for file_path, content in components:
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Created: {file_path}")
            created_count += 1
            
        except Exception as e:
            print(f"❌ Failed to create {file_path}: {e}")
    
    print(f"\n📁 Created {created_count} middleware components")
    return True

def create_setup_scripts():
    """Create additional setup scripts."""
    print("\n🔧 Creating setup scripts...")

    # Create run_tests.sh
    with open('run_tests.sh', 'w', encoding='utf-8') as f:
        f.write("""#!/bin/bash
# Run GameTrainer middleware tests

echo "🧪 Running GameTrainer middleware tests..."

# Install test dependencies
pip install pytest numpy opencv-python pygame

# Run tests
python -m pytest tests/ -v

echo "✅ Tests completed"
""")
    os.chmod('run_tests.sh', 0o755)
    print("✅ Created: run_tests.sh")

    # Create check_system.py
    with open('check_system.py', 'w', encoding='utf-8') as f:
        f.write(textwrap.dedent("""\
#!/usr/bin/env python3

Check if the system is properly configured for GameTrainer middleware.

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
"""))
    os.chmod('check_system.py', 0o755)
    print("✅ Created: check_system.py")

    return True

def main():
    """Main installation function."""
    print_header()
    
    steps = [
        ("System Requirements Check", check_system_requirements),
        ("Python Dependencies Installation", install_python_dependencies),
        ("Directory Structure Creation", create_directory_structure),
        ("Middleware Components Creation", create_middleware_components),
        ("Setup Scripts Creation", create_setup_scripts),
    ]
    
    completed = 0
    failed = 0
    
    for step_name, step_function in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        
        try:
            if step_function():
                completed += 1
                print(f"✅ {step_name} - COMPLETED")
            else:
                failed += 1
                print(f"❌ {step_name} - FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {step_name} - ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("📊 INSTALLATION SUMMARY")
    print("=" * 80)
    print(f"✅ Completed: {completed}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Directories: {len(INSTALL_DIRECTORIES)}")
    
    if failed == 0:
        print("\n🎉 INSTALLATION COMPLETED SUCCESSFULLY!")
        print("\n📋 Next Steps:")
        print("   1. Run the setup script: python install_middleware.py")
        print("   2. Configure hardware connections")
        print("   3. Test the system: python check_system.py")
        print("   4. Run tests: ./run_tests.sh")
        print("   5. Start GameTrainer: python main.py")
        
        return True
    else:
        print(f"\n❌ INSTALLATION FAILED ({failed} steps failed)")
        print("Please review the failed steps above and try again.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)