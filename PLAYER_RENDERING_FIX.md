# Player Rendering Fix

## Problem
Other players were not visible in Kitty graphics mode during multiplayer. They appeared on the minimap but not in the 3D view.

## Root Cause
The `KittyRenderer` class had the `other_players` parameter in its `render()` method but never actually used it. The renderer only drew walls, completely ignoring other players.

## Solution
Added player rendering logic to `KittyRenderer.render()`:

1. **Player Detection**: For each ray cast, check if any other players are in that ray's direction
2. **Distance Check**: Calculate distance to each player and compare with wall distance
3. **Visibility Check**: Render player sprite if they're closer than the wall
4. **Sprite Rendering**: Draw a red vertical line representing the player, scaled by distance

## Technical Details

The fix follows the same pattern as the existing ASCII renderer:

```python
# For each screen column:
1. Cast ray to find wall distance
2. Check all other players
3. Calculate angle to each player
4. If player is in this column's FOV and closer than wall:
   - Calculate sprite height based on distance
   - Draw colored rectangle (red = enemy player)
   - Skip wall rendering for this column
```

### Player Sprite Colors
- **Red (255, 50, 50)**: Other players / enemies
- Height scales with distance (closer = taller)

## Testing

To test multiplayer rendering:

```bash
# Terminal 1: Start server
cd /home/mathias/terminal-shooter
./venv/bin/python3 -m src.main --host --skip-intro

# Terminal 2: Join as client (Kitty graphics)
cd /home/mathias/terminal-shooter
./venv/bin/python3 -m src.main --join localhost --graphics kitty --skip-intro

# Or join with ASCII
./venv/bin/python3 -m src.main --join localhost --solo --skip-intro
```

Both players should now see each other in the 3D view.

## What Works Now

- ✅ ASCII mode: Players rendered as █, ▓, ●, or ○ (distance-based)
- ✅ Kitty mode: Players rendered as red vertical sprites (distance-scaled)
- ✅ Minimap: Shows player positions (already worked)
- ✅ Depth sorting: Players behind walls are hidden correctly
- ✅ FOV culling: Only render players in view cone

## Files Modified

- `src/renderer_kitty.py`: Added player rendering logic (lines ~45-100)

## Known Limitations

1. Player sprites are simple colored rectangles (future: use actual textures)
2. All other players appear red (future: team colors, player IDs)
3. No player animations yet (future: walking, shooting animations)

These are cosmetic issues and don't affect gameplay.
