# Evdev Input - Troubleshooting & Testing Guide

## Quick Start

If evdev isn't working, follow these steps in order:

### Step 1: Verify Setup
```bash
/tmp/test_evdev_diagnostics.sh
```

This checks:
- User permissions (input group)
- Device availability
- Python module installation
- Device detection

### Step 2: Test Input Detection (Interactive)
```bash
cd /home/mathias/terminal-shooter
./venv/bin/python3 /tmp/test_evdev_interactive.py
```

**What to do**: Press W, A, S, D keys during the 10-second test.

**Expected output**: Should show lines like:
```
[0.53s] FORWARD
[0.75s] FORWARD + RIGHT
[1.20s] LEFT
```

**If no output**: See troubleshooting below.

### Step 3: Run Game with Debug
```bash
cd /home/mathias/terminal-shooter
rm /tmp/evdev_debug.log kitty_debug.log
EVDEV_DEBUG=1 ./venv/bin/python3 -m src.main --evdev --solo
```

**What to check**:
1. Status line (bottom of screen) should show `SOLO | EVDEV | ...`
2. After quitting, check logs:
   ```bash
   cat kitty_debug.log | grep -i evdev
   cat /tmp/evdev_debug.log | head -20
   ```

## Common Problems & Solutions

### Problem: "Can't move at all"

**Check 1 - Is evdev active?**
```bash
# Look for this line in kitty_debug.log:
cat kitty_debug.log | grep "Evdev started"
```
✅ If found: Evdev initialized successfully  
❌ If not found: Check logs for error messages

**Check 2 - Is input being detected?**
```bash
# With EVDEV_DEBUG=1, check /tmp/evdev_debug.log
cat /tmp/evdev_debug.log
```
✅ If you see "KEY DOWN" / "KEY UP": Hardware detection works  
❌ If empty: Input not reaching evdev (see permission issues)

**Check 3 - Status line**
The bottom status should show `EVDEV`, not `STD` or `KITTY`  
❌ If showing `STD`: Evdev failed to initialize

### Problem: "Permission denied"

**Solution**: Add yourself to the `input` group
```bash
# Add to group
sudo usermod -a -G input $USER

# Verify (AFTER logging out and back in)
groups | grep input
```

⚠️ **Important**: You MUST log out and log back in for group changes to take effect!

### Problem: "No compatible keyboard found"

**Check available devices**:
```bash
# List all input devices
python3 << 'EOF'
import evdev
for device in [evdev.InputDevice(path) for path in evdev.list_devices()]:
    print(f"{device.name}: {device.path}")
EOF
```

**What to look for**: A device with "keyboard" in the name

**If none found**: 
- Are you using a USB keyboard? Try unplugging and replugging
- Bluetooth keyboard? Make sure it's connected
- Laptop keyboard? Should work automatically

### Problem: Status shows "STD" not "EVDEV"

This means evdev failed to initialize. Check `kitty_debug.log`:

```bash
cat kitty_debug.log
```

Look for lines like:
- `Evdev init error: ...` - Shows what went wrong
- `Evdev exception: ...` - Shows Python error

### Problem: Works in test but not in game

This is rare but possible. Check if:
1. Another input mode is taking priority
2. Keys are mapped incorrectly

**Debug**:
```bash
# Run with debug enabled
EVDEV_DEBUG=1 ./venv/bin/python3 -m src.main --evdev --solo

# In another terminal, watch the log
tail -f /tmp/evdev_debug.log
```

Press keys in the game. You should see `KEY DOWN` / `KEY UP` in the log.

## Comparison: Testing Each Input Mode

Test each mode to isolate the issue:

```bash
cd /home/mathias/terminal-shooter

# 1. Standard mode (baseline)
./venv/bin/python3 -m src.main --solo --skip-intro
# Can you move? (might be limited multi-key support)

# 2. Kitty protocol mode
./venv/bin/python3 -m src.main --graphics kitty --solo --skip-intro
# Can you move? (good multi-key if in Kitty terminal)

# 3. Evdev mode
./venv/bin/python3 -m src.main --evdev --solo --skip-intro
# Can you move? (should have perfect multi-key)
```

## What Should Work

With evdev working correctly:
- ✅ Press W+D simultaneously → move diagonally forward-right
- ✅ Press W+A+Shift simultaneously → move diagonally forward-left faster
- ✅ Hold W, then press D while holding W → smooth diagonal
- ✅ Zero input lag (direct hardware access)
- ✅ Status line shows "EVDEV"

## Debug Checklist

Run through this checklist:

- [ ] User in `input` group: `groups | grep input`
- [ ] Logged out and back in since adding to group
- [ ] Evdev module installed: `python3 -c "import evdev"`
- [ ] Test script detects keyboard: `/tmp/test_evdev_diagnostics.sh`
- [ ] Interactive test detects keypresses: `/tmp/test_evdev_interactive.py`
- [ ] Game initializes evdev: Check `kitty_debug.log`
- [ ] Status line shows "EVDEV" not "STD"
- [ ] With `EVDEV_DEBUG=1`, log shows key events

## Still Having Issues?

### Collect diagnostic information:

```bash
# 1. Run diagnostics
/tmp/test_evdev_diagnostics.sh > /tmp/diag.txt 2>&1

# 2. Test detection
/home/mathias/terminal-shooter/venv/bin/python3 /tmp/test_evdev_interactive.py > /tmp/test.txt 2>&1

# 3. Run game with debug
cd /home/mathias/terminal-shooter
EVDEV_DEBUG=1 ./venv/bin/python3 -m src.main --evdev --solo --skip-intro

# 4. Collect logs
cat /tmp/diag.txt
cat /tmp/test.txt  
cat kitty_debug.log
cat /tmp/evdev_debug.log
```

### Alternative: Use Different Input Mode

If evdev continues to have issues, try:

**Kitty Protocol Mode** (if using Kitty terminal):
```bash
./venv/bin/python3 -m src.main --graphics kitty --solo
```
- Supports true simultaneous input
- Works over SSH
- Requires Kitty terminal

**Pynput Mode** (if on X11):
```bash
./venv/bin/python3 -m src.main --native-input --solo
```
- Good multi-key support
- Requires X11 (not Wayland)
- Local only (no SSH)

## Files Reference

- **Test script**: `/tmp/test_evdev_interactive.py`
- **Diagnostics**: `/tmp/test_evdev_diagnostics.sh`
- **Troubleshooting**: `/tmp/evdev_troubleshooting.sh`
- **Debug log**: `/tmp/evdev_debug.log` (when EVDEV_DEBUG=1)
- **Game log**: `kitty_debug.log` (in game directory)
- **Documentation**: `EVDEV.md` (in game directory)

## Documentation

For complete technical details, see:
```bash
cat /home/mathias/terminal-shooter/EVDEV.md
```
