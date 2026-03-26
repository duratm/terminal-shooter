# Multiplayer Debug Guide

## Problem: "I don't see other players in the game"

This guide will help you diagnose and fix multiplayer visibility issues.

## Quick Diagnosis

### Test Setup

**Terminal 1 - Debug Server:**
```bash
cd ~/terminal-shooter
python3 src/network/debug_server.py
```

**Terminal 2 - Player 1:**
```bash
cd ~/terminal-shooter
python3 -m src.main --join localhost
```

**Terminal 3 - Player 2:**
```bash
cd ~/terminal-shooter
python3 -m src.main --join localhost
```

### What to Look For

#### In the Debug Server Terminal:
Watch for these events:

1. **Connection Events:**
   ```
   🔌 NEW CONNECTION ATTEMPT from ('127.0.0.1', 54321)
   📩 Received message: CONNECT
   ✅ ACCEPTED: Assigning ID 1
   ```

2. **Position Updates (every few frames):**
   ```
   📨 Event #10: POSITION_UPDATE from Player 1
      Position: (5.23, 3.45), Angle: 1.57
   ```

3. **State Broadcasts:**
   ```
   📡 Broadcasting state to 2 clients
      Player 1: (5.2, 3.4) HP:100 Alive:True
      Player 2: (20.5, 20.5) HP:100 Alive:True
   ```

4. **Shoot Events:**
   ```
   📨 Event #47: SHOOT from Player 1
      🔫 SHOT FIRED!
   ```

## Common Issues and Fixes

### Issue 1: Players Connect but No Position Updates

**Symptoms:**
- Debug server shows connections
- No POSITION_UPDATE events appear
- Server shows "Broadcasting state to X clients" but no player movement

**Cause:** Client is not sending position updates

**Fix:** Check that client network thread is running
```python
# In src/network/client.py, the update() method should be called
```

### Issue 2: Server Broadcasts but Clients Don't Receive

**Symptoms:**
- Server shows position broadcasts
- Clients don't update other_players
- Minimap doesn't show other players

**Cause:** UDP packets not reaching clients

**Fix:** Check firewall/network settings
```bash
# Test UDP connectivity
nc -u localhost 5555
```

### Issue 3: Clients Receive Data but Players Not Visible in 3D

**Symptoms:**
- Minimap shows other players (as 'P')
- 3D view doesn't show other players
- other_players list is populated in client

**Cause:** This was the original bug - renderer not drawing players

**Status:** ✅ FIXED in renderer.py

**Verify fix is applied:**
```bash
cd ~/terminal-shooter
grep -n "other_players" src/renderer.py
```

Should show:
- Line with `def render(self, game_map, x, y, angle, other_players=None):`
- Line with `if other_players:`
- Line with `render_player_column` function

### Issue 4: Players Visible but at Wrong Position

**Symptoms:**
- Players appear but don't move smoothly
- Players appear in walls
- Position jumps around

**Cause:** Network latency or position sync issues

**Fix:** Server is authoritative, check network delay
```bash
# Test network latency
ping localhost  # Should be < 1ms for localhost
```

## Manual Testing Checklist

Run through these steps in order:

### 1. Server Starts Successfully
- [ ] Debug server starts without errors
- [ ] Shows "✅ Server started on 0.0.0.0:5555"
- [ ] Shows "Waiting for players"

### 2. First Player Connects
- [ ] Client shows connection screen
- [ ] Server shows "✅ Player1 connected (ID: 1)"
- [ ] Server shows "Players online: 1/8"
- [ ] Server shows "🎮 Game started!"
- [ ] Client enters game successfully

### 3. Second Player Connects  
- [ ] Client 2 shows connection screen
- [ ] Server shows "✅ Player2 connected (ID: 2)"
- [ ] Server shows "Players online: 2/8"
- [ ] Client 2 enters game successfully

### 4. Position Updates Flow
- [ ] Player 1 moves (W/A/S/D keys)
- [ ] Server shows POSITION_UPDATE events from Player 1
- [ ] Player 2 moves
- [ ] Server shows POSITION_UPDATE events from Player 2

### 5. State Broadcasts
- [ ] Server periodically shows "📡 Broadcasting state to 2 clients"
- [ ] Both players' positions are listed

### 6. Visual Confirmation
- [ ] Player 1 can see Player 2 on minimap (as 'P')
- [ ] Player 1 can see Player 2 in 3D view (as @, O, o, or °)
- [ ] Player 2 can see Player 1 on minimap
- [ ] Player 2 can see Player 1 in 3D view
- [ ] Player size changes with distance

### 7. Shooting Works
- [ ] Player presses SPACE to shoot
- [ ] Server shows "🔫 SHOT FIRED!" event
- [ ] Other player sees the shot

## Expected Debug Server Output

Here's what a healthy multiplayer session looks like:

```
==========================================================
🔍 DEBUG SERVER MODE ENABLED
==========================================================
✅ Server started on 0.0.0.0:5555
   Waiting for players (max: 8)...

==========================================================
🔌 NEW CONNECTION ATTEMPT from ('127.0.0.1', 52341)
==========================================================
📩 Received message: CONNECT
📦 Message data: {'player_id': 0, 'player_name': 'Player'}
✅ ACCEPTED: Assigning ID 1
   Spawn point: (3.5, 2.5)
   Total players: 1/8
✅ Player connected (ID: 1) from ('127.0.0.1', 52341)
   Players online: 1/8

🎮 Game started!

==========================================================
🔌 NEW CONNECTION ATTEMPT from ('127.0.0.1', 52342)
==========================================================
📩 Received message: CONNECT
📦 Message data: {'player_id': 0, 'player_name': 'Player'}
✅ ACCEPTED: Assigning ID 2
   Spawn point: (20.5, 20.5)
   Total players: 2/8
✅ Player connected (ID: 2) from ('127.0.0.1', 52342)
   Players online: 2/8

📨 Event #10: POSITION_UPDATE from Player 1
   Position: (3.50, 2.87), Angle: 0.00

📨 Event #20: POSITION_UPDATE from Player 2
   Position: (20.50, 20.12), Angle: 3.14

📡 Broadcasting state to 2 clients
   Player 1: (3.5, 3.2) HP:100 Alive:True
   Player 2: (20.5, 19.8) HP:100 Alive:True

📨 Event #30: POSITION_UPDATE from Player 1
   Position: (3.50, 3.45), Angle: 0.52
```

## Network Architecture

Understanding how the multiplayer works:

```
[Client 1] <-- TCP/UDP --> [Server] <-- TCP/UDP --> [Client 2]
    |                          |                          |
    v                          v                          v
  Game                   Game State                     Game
 Render                 Authority                      Render
```

1. **TCP Connection (Initial):**
   - Client sends CONNECT message
   - Server responds with CONNECT_ACK
   - Assigns player ID and spawn point

2. **UDP Gameplay (Continuous):**
   - Client sends: POSITION_UPDATE (20/sec)
   - Client sends: SHOOT (on space press)
   - Server sends: POSITION_UPDATE for all players (30/sec)
   - Server sends: SHOOT broadcasts
   - Server sends: HIT/DIED/RESPAWN events

3. **Rendering (Local):**
   - Client receives other_players updates
   - Game.update() populates self.other_players list
   - Renderer.render() receives other_players
   - Renderer checks each ray for player intersections
   - Draws players if closer than walls

## Quick Fixes

### "Server is running but players can't connect"
```bash
# Check if port is available
lsof -i :5555

# Try different port
python3 -m src.main --host --port 5556
python3 -m src.main --join localhost:5556
```

### "Connected but can't see each other"
```bash
# Verify fix is present
grep "other_players" src/renderer.py | head -5

# Should show the parameter in render() function
```

### "Players appear but in wrong place"
```bash
# Check network delay
ping -c 10 localhost

# Should be < 1ms for localhost
# If > 50ms, there may be network issues
```

## Getting More Help

If none of these solutions work:

1. **Capture debug output:**
   ```bash
   python3 src/network/debug_server.py > server_debug.log 2>&1
   ```

2. **Check what the client is doing:**
   ```python
   # Add print statements to src/network/client.py
   # In process_messages() method:
   print(f"Received: {msg.msg_type} with data: {msg.data}")
   ```

3. **Verify renderer receives players:**
   ```python
   # Add to src/game.py in render() method:
   print(f"Rendering with {len(self.other_players)} other players")
   ```

## Alternative Test Scripts

### Simple Server Test
```bash
./test_multiplayer.sh
# Choose option 1 for debug server
```

### Connection Diagnostic
```bash
./test_multiplayer.sh
# Choose option 4 for diagnostics
```

---

## Summary

The most common issue is that the renderer fix is not applied. Verify that:

1. ✅ `src/renderer.py` has `other_players` parameter in `render()` method
2. ✅ `src/game.py` passes `self.other_players` to renderer
3. ✅ Players are spawning at different locations (not on top of each other)
4. ✅ Server is receiving and broadcasting position updates

Use the debug server to see exactly what's happening on the network level!
