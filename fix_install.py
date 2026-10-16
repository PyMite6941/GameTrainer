import sys
import textwrap

with open('install_middleware.py.backup', 'r') as f:
    lines = f.readlines()

# Find the function create_setup_scripts
start_idx = None
for i, line in enumerate(lines):
    if line.strip() == 'def create_setup_scripts():':
        start_idx = i
        break

if start_idx is None:
    print("Could not find function start")
    sys.exit(1)

# Find the end of the function: look for the next function definition or a line with indent 0 that is not empty
end_idx = None
for i in range(start_idx + 1, len(lines)):
    # Check if this line is a function definition (starts with 'def ' and at indent 0)
    if lines[i].startswith('def ') and lines[i].find('def ') == 0:  # indent 0
        end_idx = i
        break
    # Also stop if we hit a line that is not indented (and not empty) and not part of the function
    stripped = lines[i].strip()
    if stripped and not lines[i].startswith('    ') and not lines[i].startswith('\t'):
        end_idx = i
        break

if end_idx is None:
    end_idx = len(lines)

# Now we have the function from start_idx to end_idx-1
# We want to replace lines[start_idx:end_idx] with the fixed function.

fixed_function = '''def create_setup_scripts():
    """Create additional setup scripts."""
    print("\\n🔧 Creating setup scripts...")

    # Create run_tests.sh
    with open('run_tests.sh', 'w', encoding='utf-8') as f:
        f.write("""#!/bin/bash
# Run GameTrainer middleware tests

echo \"🧪 Running GameTrainer middleware tests...\"

# Install test dependencies
pip install pytest numpy opencv-python pygame

# Run tests
python -m pytest tests/ -v

echo \"✅ Tests completed"""
)
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
    print(\"🔍 Checking GameTrainer middleware system...\")

    # Check hardware
    print(\"\\n1. Hardware Check:\")

    # Check HDMI capture
    hdmi_capture = HDMI_Capture()
    if hdmi_capture.is_supported():
        print(\"   ✅ HDMI capture supported\")
    else:
        print(\"   ❌ HDMI capture not supported\")

    # Check USB capture
    usb_capture = USB_Capture()
    if usb_capture.is_connected():
        print(\"   ✅ USB capture connected\")
    else:
        print(\"   ❌ USB capture not connected\")

    # Check frame processor
    frame_processor = Frame_Processor()
    if frame_processor.is_configured():
        print(\"   ✅ Frame processor configured\")
    else:
        print(\"   ❌ Frame processor not configured\")

    print(\"\\n2. Configuration Check:\")

    # Check config file
    import json
    try:
        with open('config/middleware_config.json', 'r') as f:
            config = json.load(f)

        print(\"   ✅ Configuration file exists\")
        print(f\"   • Resolution: {config['hardware']['resolution']}\")
        print(f\"   • Frame rate: {config['hardware']['frame_rate']} FPS\")

    except Exception as e:
        print(f\"   ❌ Configuration file error: {e}\")

    print(\"\\n3. Console Support Check:\")

    # Check console support
    try:
        with open('config/middleware_config.json', 'r') as f:
            config = json.load(f)

        consoles = config['console_support']
        for console, supported in consoles.items():
            status = \"✅\" if supported else \"❌\"
            print(f\"   {status} {console.replace('_', ' ').title()}: {'Supported' if supported else 'Not Supported'}\")

    except Exception as e:
        print(f\"   ❌ Console support check error: {e}\")

    print(\"\\n✅ System check completed\")

if __name__ == \"__main__\":
    main()
"""))
    os.chmod('check_system.py', 0o755)
    print("✅ Created: check_system.py")

    return True
'''

# Now replace the function
new_lines = lines[:start_idx] + [fixed_function] + lines[end_idx:]

with open('install_middleware.py', 'w') as f:
    f.writelines(new_lines)

print("Fixed install_middleware.py")
