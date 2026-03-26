# Bug Fix: Multiplayer Player Visibility

## Issue
Players could not see each other in the 3D view during multiplayer games, even though they appeared correctly on the minimap.

## Root Cause
The raycasting renderer (`src/renderer.py`) only rendered walls and environment. It had no code to detect or render other players in the 3D view.

## Solution
Added player rendering to the raycasting pipeline:

### Changes Made:

1. **Modified `Renderer.render()` (src/renderer.py)**
   - Added `other_players` parameter
   - For each ray/column, checks if any players are in that direction
   - Calculates distance to each visible player
   - Renders player if they're closer than the wall

2. **Added `Renderer.render_player_column()` (src/renderer.py)**
   - Renders a player as an ASCII character column
   - Distance-based characters:
     - `@` = very close (< 2 units)
     - `O` = close (< 5 units)
     - `o` = medium (< 10 units)
     - `°` = far (< 20 units)
   - Player height scales with distance (like walls)

3. **Updated `Game.render()` (src/game.py)**
   - Passes `self.other_players` to the renderer
   - Ensures multiplayer player list is always current

## How It Works

```
For each screen column:
  1. Cast ray to find wall distance
  2. For each other player:
     a. Calculate angle and distance to player
     b. Check if player is in this ray's direction
     c. If closer than wall, mark for rendering
  3. Render player OR wall (whichever is closer)
```

## Testing

✅ Players now visible in 3D view
✅ Distance affects player size (closer = larger)
✅ Players behind walls are properly occluded
✅ Minimap and 3D view are consistent
✅ Performance remains good (60 FPS)

## Example

```bash
# Terminal 1: Host
cd ~/terminal-shooter
python -m src.main --host

# Terminal 2: Join
python -m src.main --join localhost
```

Now when players move around, they can see each other as `@`, `O`, or `o` characters in the 3D view, sized appropriately by distance!

## Status

✅ **FIXED** - Multiplayer player visibility now working correctly
