import sys

with open('install_middleware.py.backup', 'r') as f:
    lines = f.readlines()

# We'll write to a new list
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Add import for textwrap after the existing imports
    if line.strip() == 'import os':
        new_lines.append(line)
        i += 1
        # Add the next lines until we have added all the imports
        while i < len(lines) and lines[i].startswith('import ') or lines[i].startswith('from '):
            new_lines.append(lines[i])
            i += 1
        # Now add the textwrap import
        new_lines.append('import textwrap\\n')
        continue

    # Replace the write for check_system.py
    if line.strip() == 'def create_setup_scripts():':
        # We will copy the function header and then the body until we find the write for check_system.py
        new_lines.append(line)
        i += 1
        # Copy until we find the line that starts with '        f.write(\"\"\"#!/usr/bin/env python3'
        while i < len(lines) and not lines[i].strip().startswith('f.write(\"\"\"#!/usr/bin/env python3'):
            new_lines.append(lines[i])
            i += 1
        # Now we are at the line that starts the write for check_system.py
        # We will replace the next two lines (the write and the closing triple quotes) with our new write
        # But note: in the backup, the write is two lines: the opening and the closing triple quotes.
        # We want to replace these two lines with our new write.
        # Skip the two lines
        i += 2  # skip the two lines of the old write

        # Now we need to skip the content that was outside the string until we get to the os.chmod line
        # We know that after the old write, the next lines are the content that was meant to be in the string,
        # but we are going to put them inside the string, so we skip them until we see the os.chmod line.
        # We'll skip until we find a line that starts with '        os.chmod(\'check_system.py\', 0o755)'
        while i < len(lines) and not lines[i].strip().startswith('os.chmod(\'check_system.py\', 0o755)'):
            i += 1
        # Now we are at the os.chmod line, we want to keep it and the following lines until the end of the function.
        # But note: we have to adjust the indentation? We are going to write the new write line now.

        # Write the new write for check_system.py using textwrap.dedent
        new_lines.append('        f.write(textwrap.dedent(\"\"\"\\n')
        new_lines.append(' #!/usr/bin/env python3\\n')
        new_lines.append('\\n')
        new_lines.append(' Check if the system is properly configured for GameTrainer middleware.\\n')
        new_lines.append('\\n')
        new_lines.append(' # Import middleware components\\n')
        new_lines.append(' from middleware.capture.hdmi_capture import HDMI_Capture\\n')
        new_lines.append(' from middleware.capture.usb_capture import USB_Capture\\n')
        new_lines.append(' from middleware.analysis.frame_processor import Frame_Processor\\n')
        new_lines.append('\\n')
        new_lines.append(' def main():\\n')
        new_lines.append('     print(\\\"🔍 Checking GameTrainer middleware system...\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     # Check hardware\\n')
        new_lines.append('     print(\\\"\\\\n1. Hardware Check:\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     # Check HDMI capture\\n')
        new_lines.append('     hdmi_capture = HDMI_Capture()\\n')
        new_lines.append('     if hdmi_capture.is_supported():\\n')
        new_lines.append('         print(\\\"   ✅ HDMI capture supported\\\")\\n')
        new_lines.append('     else:\\n')
        new_lines.append('         print(\\\"   ❌ HDMI capture not supported\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     # Check USB capture\\n')
        new_lines.append('     usb_capture = USB_Capture()\\n')
        new_lines.append('     if usb_capture.is_connected():\\n')
        new_lines.append('         print(\\\"   ✅ USB capture connected\\\")\\n')
        new_lines.append('     else:\\n')
        new_lines.append('         print(\\\"   ❌ USB capture not connected\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     # Check frame processor\\n')
        new_lines.append('     frame_processor = Frame_Processor()\\n')
        new_lines.append('     if frame_processor.is_configured():\\n')
        new_lines.append('         print(\\\"   ✅ Frame processor configured\\\")\\n')
        new_lines.append('     else:\\n')
        new_lines.append('         print(\\\"   ❌ Frame processor not configured\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     print(\\\"\\\\n2. Configuration Check:\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     # Check config file\\n')
        new_lines.append('     import json\\n')
        new_lines.append('     try:\\n')
        new_lines.append('         with open(\\'config/middleware_config.json\\', \\\"r\\") as f:\\n')
        new_lines.append('             config = json.load(f)\\n')
        new_lines.append('\\n')
        new_lines.append('         print(\\\"   ✅ Configuration file exists\\\")\\n')
        new_lines.append('         print(f\\\"   • Resolution: {config[\\\"hardware\\\"][\\\"resolution\\\"]}\\\")\\n')
        new_lines.append('         print(f\\\"   • Frame rate: {config[\\\"hardware\\\"][\\\"frame_rate\\\"]} FPS\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     except Exception as e:\\n')
        new_lines.append('         print(f\\\"   ❌ Configuration file error: {e}\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     print(\\\"\\\\n3. Console Support Check:\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     # Check console support\\n')
        new_lines.append('     try:\\n')
        new_lines.append('         with open(\\'config/middleware_config.json\\', \\\"r\\") as f:\\n')
        new_lines.append('             config = json.load(f)\\n')
        new_lines.append('\\n')
        new_lines.append('         consoles = config[\\\"console_support\\\"]\\n')
        new_lines.append('         for console, supported in consoles.items():\\n')
        new_lines.append('             status = \\\"✅\\\" if supported else \\\"❌\\\"\\n')
        new_lines.append('             print(f\\\"   {status} {console.replace(\\\"_\\\", \\\" \\\").title()}: {\\\"Supported\\\" if supported else \\\"Not Supported\\\"}\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     except Exception as e:\\n')
        new_lines.append('         print(f\\\"   ❌ Console support check error: {e}\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     print(\\\"\\\\n✅ System check completed\\\")\\n')
        new_lines.append('\\n')
        new_lines.append('     if __name__ == \\\"__main__\\\":\\n')
        new_lines.append('         main()\\n')
        new_lines.append('\"\"\"))\\n')
        # Now we are at the os.chmod line in the original lines, we want to keep it and the following lines.
        # But note: we have already skipped the content that was outside the string, and we are at the os.chmod line.
        # We will now add the os.chmod line and the rest of the function.
        # However, note that we have already skipped the os.chmod line? We stopped at the line that starts with os.chmod, but we haven't added it yet.
        # We will add it now.
        # But note: we are still in the while loop and we haven't incremented i for the os.chmod line.
        # We will add the os.chmod line and then continue.

        # We do not increment i here because we want to process the os.chmod line in the next iteration.
        continue

    # If we didn't match any of the above, just add the line.
    new_lines.append(line)
    i += 1

# Write the new file
with open('install_middleware.py', 'w') as f:
    f.writelines(new_lines)

print("Fixed install_middleware.py")
