# How to See Server Events

You asked: **"How could I see what events my server are receiving?"**

## Answer: Use the Debug Server

I've created a special debug version of the server that shows ALL events in real-time.

### Quick Start

**Terminal 1 - Start Debug Server:**
```bash
cd ~/terminal-shooter
python3 src/network/debug_server.py
```

**Terminal 2 - Join as Player:**
```bash
cd ~/terminal-shooter
python3 -m src.main --join localhost
```

### What You'll See

The debug server shows every event:

```
==========================================================
🔍 DEBUG SERVER MODE ENABLED
==========================================================
✅ Server started on 0.0.0.0:5555
   Waiting for players (max: 8)...

🔌 NEW CONNECTION ATTEMPT from ('127.0.0.1', 54321)
📩 Received message: CONNECT
📦 Message data: {'player_id': 0, 'player_name': 'Player'}
✅ ACCEPTED: Assigning ID 1
   Spawn point: (3.5, 2.5)
   Total players: 1/8

📨 Event #10: POSITION_UPDATE from Player 1
   Position: (3.50, 2.87), Angle: 0.00

📨 Event #20: POSITION_UPDATE from Player 1
   Position: (3.50, 3.45), Angle: 0.52

📨 Event #47: SHOOT from Player 1
   🔫 SHOT FIRED!

📡 Broadcasting state to 1 clients
   Player 1: (3.5, 3.5) HP:100 Alive:True
```

## Why You Can't See Other Players

The most common reason: **spawn points are too far apart!**

- Player 1 spawns at (3.5, 2.5)
- Player 2 spawns at (20.5, 20.5)
- Distance: ~25 units
- **Max render distance: 20 units**

### Solution: Walk Towards Each Other

1. Press **W** to move forward
2. Use **LEFT/RIGHT arrows** to turn
3. Watch the **minimap** (top right) to see where the other player is
4. When you get within 20 units, they'll appear in your 3D view as:
   - `@` (very close, < 2 units)
   - `O` (close, < 5 units)
   - `o` (medium, < 10 units)
   - `°` (far, < 20 units)

## Files Created for You

1. **`src/network/debug_server.py`** - Debug server with detailed logging
2. **`test_multiplayer.sh`** - Helper script for testing
3. **`test_rendering.py`** - Test that rendering works
4. **`MULTIPLAYER_DEBUG_GUIDE.md`** - Comprehensive debugging guide
5. **`QUICK_DEBUG.md`** - Quick troubleshooting steps

## Quick Test

To verify everything is working:

```bash
# Run the rendering test
cd ~/terminal-shooter
python3 test_rendering.py
```

Should show:
```
✅ ALL TESTS PASSED
✅ Player rendering is working correctly!
```

## The Root Cause

Your original bug report was correct - players couldn't see each other. I fixed the rendering code to draw players in the 3D view. That fix IS working.

However, you may still not see players because:
- They're > 20 units away (walk closer!)
- You're not facing them (use arrow keys to turn)
- There's a wall between you (check minimap)

**Use the debug server to see EXACTLY what's happening on the network level!**
