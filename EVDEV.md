# EVDEV Input Mode for Terminal Shooter

## What is Evdev?

Evdev (Event Device) is a Linux kernel interface that allows programs to read input directly from hardware devices, bypassing display servers like X11 or Wayland.

## Why Use Evdev?

- **True simultaneous key detection**: Press W+A+D at the same time and all are detected
- **Works on Wayland**: Doesn't require X11
- **Works in TTY/console**: Can run outside a graphical environment
- **Lower latency**: Direct hardware access
- **No display server limitations**: Bypasses compositor input handling

## Requirements

1. **Linux system** (uses `/dev/input/*` devices)
2. **User must be in `input` group**:
   ```bash
   sudo usermod -a -G input $USER
   # Log out and log back in for changes to take effect
   ```
3. **Python evdev module** (already installed in venv)

## How to Use

Run the game with the `--evdev` flag:

```bash
cd terminal-shooter
./venv/bin/python3 -m src.main --evdev --solo
```

You can combine it with other flags:
```bash
# Evdev + Kitty graphics
./venv/bin/python3 -m src.main --evdev --graphics kitty --solo

# Evdev in multiplayer
./venv/bin/python3 -m src.main --evdev --host

# Enable debug logging
EVDEV_DEBUG=1 ./venv/bin/python3 -m src.main --evdev --solo
```

## Testing Evdev

1. **Run diagnostics**:
   ```bash
   /tmp/test_evdev_diagnostics.sh
   ```

2. **Test input detection** (interactive, 10 seconds):
   ```bash
   /home/mathias/terminal-shooter/venv/bin/python3 /tmp/test_evdev_interactive.py
   ```

3. **Check debug logs**:
   ```bash
   # Evdev input events
   tail -f /tmp/evdev_debug.log
   
   # Game initialization
   tail -f /home/mathias/terminal-shooter/kitty_debug.log
   ```

## Troubleshooting

### "Permission denied" error
- **Cause**: User not in `input` group
- **Fix**: 
  ```bash
  sudo usermod -a -G input $USER
  # Then log out and log back in
  ```
- **Verify**: `groups` should show `input`

### "No compatible keyboard found"
- **Cause**: Evdev can't find a keyboard with WASD keys
- **Check devices**:
  ```bash
  ls -l /dev/input/event*
  ```
- **List all input devices**:
  ```bash
  python3 -c "import evdev; [print(d.name, d.path) for d in [evdev.InputDevice(p) for p in evdev.list_devices()]]"
  ```

### Can't move in game
- **Check that evdev initialized**:
  ```bash
  cat /home/mathias/terminal-shooter/kitty_debug.log
  ```
  Should show: `Evdev started on [keyboard name]`

- **Check input is being detected**:
  ```bash
  # Clear log and play briefly
  rm /tmp/evdev_debug.log
  # Start game, press some keys, quit
  cat /tmp/evdev_debug.log
  ```
  Should show `KEY DOWN` and `KEY UP` events

- **Verify status line shows "EVDEV"**:
  The HUD should display `SOLO | EVDEV | ...`

### Input lag or missed keys
- Evdev reads at hardware level with minimal latency
- If you experience issues, it's likely a different problem
- Try without evdev first to compare

## How It Works

1. **Device Discovery**: Scans `/dev/input/event*` for keyboards with WASD support
2. **Background Thread**: Runs a separate thread to read input events
3. **Event Processing**: Translates kernel key codes to game actions
4. **State Tracking**: Maintains pressed key state in a set
5. **Game Integration**: Game loop queries key state each frame

## Comparison with Other Input Modes

| Mode | Multi-key | Wayland | SSH | Best For |
|------|-----------|---------|-----|----------|
| **Evdev** | ✅ Perfect | ✅ Yes | ❌ No | Local Linux play |
| **Pynput** | ✅ Good | ⚠️ Limited | ❌ No | Local X11 |
| **Kitty Protocol** | ✅ Good | ✅ Yes | ✅ Yes | Kitty terminal |
| **Standard Curses** | ⚠️ Decay hack | ✅ Yes | ✅ Yes | Fallback |

## Security Note

Evdev requires read access to `/dev/input/*` devices. This is why you must be in the `input` group. Do not run the game as root just to use evdev - add yourself to the group instead.

## Implementation Details

- **File**: `src/input_evdev.py`
- **Thread-safe**: Uses `select()` for non-blocking reads
- **Key mapping**: Maps kernel key codes (e.g., `KEY_W=17`) to game keys
- **Clean shutdown**: Stops thread gracefully on game exit
