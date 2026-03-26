# How to Debug Multiplayer Visibility Issues

## Quick Start

**Problem:** You can't see other players in the game, even though they're connected.

**Solution:** Follow these steps to diagnose and fix the issue.

---

## Step 1: Verify the Rendering Fix is Applied

Run the rendering test:

```bash
cd ~/terminal-shooter
python3 test_rendering.py
```

**Expected output:**
```
✅ ALL TESTS PASSED
✅ Player rendering is working correctly!
```

If this passes, the rendering code is working. Continue to Step 2.

---

## Step 2: Start the Debug Server

The debug server shows you EXACTLY what events are being received.

**Terminal 1 (Debug Server):**
```bash
cd ~/terminal-shooter
python3 src/network/debug_server.py
```

You should see:
```
🔍 DEBUG SERVER MODE ENABLED
✅ Server started on 0.0.0.0:5555
   Waiting for players (max: 8)...
```

---

## Step 3: Connect Players and Watch Events

**Terminal 2 (Player 1):**
```bash
cd ~/terminal-shooter  
python3 -m src.main --join localhost
```

**Terminal 3 (Player 2):**
```bash
cd ~/terminal-shooter
python3 -m src.main --join localhost
```

---

## Step 4: Check What the Debug Server Shows

### What You SHOULD See:

#### When Player 1 Connects:
```
🔌 NEW CONNECTION ATTEMPT from ('127.0.0.1', 54321)
📩 Received message: CONNECT
✅ ACCEPTED: Assigning ID 1
   Spawn point: (3.5, 2.5)
   Total players: 1/8
```

#### When Player 2 Connects:
```
🔌 NEW CONNECTION ATTEMPT from ('127.0.0.1', 54322)
📩 Received message: CONNECT
✅ ACCEPTED: Assigning ID 2
   Spawn point: (20.5, 20.5)
   Total players: 2/8
```

#### During Gameplay (every few seconds):
```
📨 Event #10: POSITION_UPDATE from Player 1
   Position: (3.50, 3.20), Angle: 0.52

📨 Event #20: POSITION_UPDATE from Player 2
   Position: (20.30, 19.85), Angle: 3.14

📡 Broadcasting state to 2 clients
   Player 1: (3.5, 3.2) HP:100 Alive:True
   Player 2: (20.3, 19.8) HP:100 Alive:True
```

---

## Common Issues and Solutions

### Issue A: Players Spawn Too Far Apart

**Symptoms:**
- Debug server shows both players connected
- Position updates are flowing
- But you can't see each other in the game

**Cause:** Default spawn points are ~24 units apart, but max render distance is 20 units!

**Solution:** Walk towards each other! You need to be within 20 units to see each other.

**To verify this is the issue:**
Look at spawn positions in debug server output:
```
Player 1 spawn: (3.5, 2.5)
Player 2 spawn: (20.5, 20.5)
Distance = sqrt((20.5-3.5)² + (20.5-2.5)²) = ~24.7 units
```

**Fix:** Have one player move towards the other. Use WASD keys to walk forward. Watch the minimap - when the other player's 'P' marker gets close, they should appear in 3D view.

---

### Issue B: Not Facing Each Other

**Symptoms:**
- Players are close together (< 20 units)
- Still can't see each other

**Cause:** Field of view is 60 degrees. You need to turn to face the other player.

**Solution:**
1. Look at the minimap (top right)
2. See where the other player 'P' is
3. Use LEFT/RIGHT arrow keys to rotate your view
4. Turn until you're facing the other player's direction

---

### Issue C: Server Not Receiving Position Updates

**Symptoms:**
- Debug server shows connections
- But NO position update events appear

**Cause:** Client is not sending UDP updates to server.

**Check in game client code:**  
The client should be calling `client.update()` every frame.

**Temporary workaround:** Restart both clients.

---

### Issue D: Walls Blocking View

**Symptoms:**
- You're close to the other player
- You're facing them
- But still can't see them

**Cause:** There's a wall between you. Player rendering includes occlusion - walls hide players behind them.

**Solution:** Move to a position with clear line of sight. Use the minimap to navigate.

---

## Expected Gameplay

When everything is working correctly:

1. **At Start:**
   - Player 1 spawns at (3.5, 2.5) - top-left area
   - Player 2 spawns at (20.5, 20.5) - bottom-right area
   - **Distance: ~25 units (TOO FAR TO SEE!)**

2. **After Moving:**
   - Player 1 walks forward (W key) towards bottom-right
   - Player 2 walks forward (W key) towards top-left
   - Watch minimap - other player marker gets closer

3. **When Within Range (< 20 units):**
   - Use arrow keys to rotate and face each other
   - Other player appears as:
     - `@` if very close (< 2 units)
     - `O` if close (< 5 units)  
     - `o` if medium (< 10 units)
     - `°` if far (< 20 units)

4. **Shooting:**
   - Press SPACE to shoot
   - If you hit the other player, they take damage
   - Respawn after 3 seconds if killed

---

## Still Not Working?

### Add Debug Output to Client

Edit `src/game.py` and add this after line 142:

```python
# Get other players from client
self.other_players = list(self.client.other_players.values())
print(f"[DEBUG] Other players: {len(self.other_players)}")  # ADD THIS LINE
if self.other_players:
    for p in self.other_players:
        dx = p.x - self.player.x
        dy = p.y - self.player.y  
        dist = (dx*dx + dy*dy)**0.5
        print(f"[DEBUG]   Player {p.player_id} at distance {dist:.1f}")  # ADD THIS LINE
```

This will print in the game client terminal:
```
[DEBUG] Other players: 1
[DEBUG]   Player 2 at distance 24.7
```

If distance > 20, you're too far apart!

---

## Test with Alternative Helper Script

Use the test script for easier debugging:

```bash
cd ~/terminal-shooter
./test_multiplayer.sh
```

Choose option 1 for debug server, then in other terminals choose option 3 to connect as clients.

---

## Network Checklist

- [ ] Debug server shows "Server started on 0.0.0.0:5555"
- [ ] Client 1 connects successfully (ID: 1 assigned)
- [ ] Client 2 connects successfully (ID: 2 assigned)  
- [ ] Server shows POSITION_UPDATE events from both players
- [ ] Server shows "Broadcasting state to 2 clients"
- [ ] Players are within 20 units of each other
- [ ] Players are facing each other (check minimap direction)
- [ ] No walls between players (check minimap)
- [ ] Player appears in 3D view as @, O, o, or ° character

---

## Summary

**The most common issue:** Players spawn 24+ units apart but can only see each other within 20 units.

**The solution:** Walk towards each other using WASD keys while watching the minimap.

**To verify everything works:** Run the debug server and watch for position updates and state broadcasts.

The rendering code IS working (verified by test_rendering.py). The issue is likely distance or facing direction!
