# EVDEV NOT WORKING - DEBUG STEPS

You reported that WASD keys don't work, but mouse and spacebar DO work.

This tells us:
- ✓ Game is running
- ✓ Curses input works (mouse, spacebar)
- ✗ WASD movement doesn't work (should come from evdev)

## Let's diagnose step by step:

### STEP 1: Test evdev hardware detection
Run this 8-second test and press WASD keys:

```bash
cd /home/mathias/terminal-shooter
./venv/bin/python3 /tmp/test_evdev_active_keys.py
```

**Expected**: You should see lines like:
```
[0.52s] active_keys = {'w'}
[0.75s] get_key_state = ['w']
```

**If you see output**: Evdev is detecting your keys ✓  
**If no output**: Evdev is NOT detecting keys → hardware/permission issue

---

### STEP 2: Run game with FULL debug logging

```bash
cd /home/mathias/terminal-shooter
rm -f /tmp/evdev_debug.log /tmp/evdev_game_sync.log kitty_debug.log

EVDEV_DEBUG=1 ./venv/bin/python3 -m src.main --evdev --solo --skip-intro
```

**In the game**:
1. Check status line (bottom) - should say `SOLO | EVDEV | ...`
2. Press W key 5 times
3. Press A key 5 times
4. Try to move around
5. Quit (press Q)

**After quitting**, check the logs:

```bash
echo "=== HARDWARE EVENTS (evdev thread) ==="
cat /tmp/evdev_debug.log | head -30
echo
echo "=== GAME SYNC (main loop) ==="
cat /tmp/evdev_game_sync.log | head -30
echo
echo "=== INITIALIZATION ==="
cat kitty_debug.log
```

---

### STEP 3: Analyze the logs

#### Scenario A: evdev_debug.log is EMPTY
```
=== HARDWARE EVENTS (evdev thread) ===
cat: /tmp/evdev_debug.log: No such file or directory
```

**Problem**: Evdev is not seeing any key events at hardware level.

**Possible causes**:
1. Wrong keyboard device selected
2. Terminal is grabbing input before evdev
3. Wayland compositor interference

**Try**:
```bash
# List all input devices
python3 << 'EOF'
import evdev
for d in [evdev.InputDevice(p) for p in evdev.list_devices()]:
    print(f"{d.name}: {d.path}")
    caps = d.capabilities()
    if evdev.ecodes.EV_KEY in caps:
        print(f"  Has keyboard events")
EOF
```

---

#### Scenario B: evdev_debug.log HAS events, but game_sync.log is EMPTY
```
=== HARDWARE EVENTS ===
KEY DOWN: w (code=17) active_keys={'w'}
KEY UP: w (code=17) active_keys=set()
KEY DOWN: a (code=30) active_keys={'a'}

=== GAME SYNC ===
cat: /tmp/evdev_game_sync.log: No such file or directory
```

**Problem**: Hardware detection works, but game isn't syncing the state.

**This is a BUG in the game code.** The sync logic isn't running or isn't working.

**Workaround**: Use Kitty Protocol mode instead:
```bash
./venv/bin/python3 -m src.main --graphics kitty --solo
```

---

#### Scenario C: BOTH logs have events
```
=== HARDWARE EVENTS ===
KEY DOWN: w (code=17) active_keys={'w'}
KEY UP: w (code=17) active_keys=set()

=== GAME SYNC ===
[1234.56] w: False -> True
[1234.58] Active keys: ['w']
[1234.60] w: True -> False
```

**Problem**: Input is being detected AND synced, but player still doesn't move.

**This is a BUG in the movement code.**

---

### STEP 4: If all else fails - try other input modes

#### Option A: Kitty Protocol (best alternative)
```bash
# Only works in Kitty terminal
./venv/bin/python3 -m src.main --graphics kitty --solo
```
✓ True simultaneous input  
✓ Works over SSH  
✓ Requires Kitty terminal

#### Option B: Standard curses (always works)
```bash
./venv/bin/python3 -m src.main --solo
```
⚠️ Limited simultaneous keys (uses decay hack)  
✓ Works everywhere

---

## Quick Reference Commands

```bash
# Test 1: Hardware detection (8 sec)
cd /home/mathias/terminal-shooter
./venv/bin/python3 /tmp/test_evdev_active_keys.py

# Test 2: Full debug game session
rm -f /tmp/*.log kitty_debug.log
EVDEV_DEBUG=1 ./venv/bin/python3 -m src.main --evdev --solo --skip-intro

# Check logs after Test 2
cat /tmp/evdev_debug.log | head -30
cat /tmp/evdev_game_sync.log | head -30
cat kitty_debug.log

# Alternative: Try Kitty protocol
./venv/bin/python3 -m src.main --graphics kitty --solo
```

---

## What to share if you need help

Run these and share the output:

```bash
# System info
groups | grep input
uname -a

# Hardware test result
./venv/bin/python3 /tmp/test_evdev_active_keys.py 2>&1

# Debug logs from game
cat /tmp/evdev_debug.log
cat /tmp/evdev_game_sync.log  
cat kitty_debug.log
```
