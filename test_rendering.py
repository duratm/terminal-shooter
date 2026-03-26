#!/usr/bin/env python3
"""
Quick multiplayer visibility test.
Run this to verify the renderer can see other players.
"""

import sys
import os

# Add parent directory to path  
sys.path.insert(0, os.path.dirname(__file__))

from src.renderer import Renderer
from src.map import create_default_map
from src.player import Player

def test_player_rendering():
    """Test that renderer can draw other players."""
    print("\n" + "="*60)
    print("🧪 Player Rendering Test")
    print("="*60 + "\n")
    
    # Create renderer and map
    renderer = Renderer(width=80, height=24)
    game_map = create_default_map()
    
    # Create local player at spawn 1
    local_player = Player(3.5, 2.5, angle=0.0, player_id=1)
    
    # Create other player at a visible distance (within 20 unit max_depth)
    # Place them 10 units away in front of player
    other_player = Player(13.5, 2.5, angle=3.14, player_id=2)
    other_players = [other_player]
    
    print(f"✅ Created local player at ({local_player.x}, {local_player.y})")
    print(f"✅ Created other player at ({other_player.x}, {other_player.y})")
    print(f"   Distance: {((local_player.x - other_player.x)**2 + (local_player.y - other_player.y)**2)**0.5:.2f} units\n")
    
    # Test 1: Render without other players (old behavior)
    print("Test 1: Render WITHOUT other_players parameter")
    frame_without = renderer.render(game_map, local_player.x, local_player.y, local_player.angle)
    has_player_chars_without = any('@' in row or 'O' in row or 'o' in row for row in frame_without)
    
    if has_player_chars_without:
        print("   ⚠️  Found player characters (unexpected)")
    else:
        print("   ✅ No player characters (expected)")
    
    # Test 2: Render with other players (new behavior)
    # Make sure we're facing the right direction to see the player
    import math
    dx = other_player.x - local_player.x
    dy = other_player.y - local_player.y
    angle_to_player = math.atan2(dy, dx)
    
    print("\nTest 2: Render WITH other_players parameter")
    print(f"   Facing angle: {angle_to_player:.2f} rad to look at other player")
    frame_with = renderer.render(game_map, local_player.x, local_player.y, angle_to_player, other_players)
    has_player_chars_with = any('@' in row or 'O' in row or 'o' in row or '°' in row for row in frame_with)
    
    if has_player_chars_with:
        print("   ✅ Found player characters (expected)")
        
        # Count player characters
        player_char_count = sum(row.count('@') + row.count('O') + row.count('o') for row in frame_with)
        print(f"   📊 Player character count: {player_char_count}")
    else:
        print("   ❌ No player characters (BUG!)")
        print("\n" + "!"*60)
        print("! ERROR: Player rendering is NOT working!")
        print("! The fix may not be applied correctly.")
        print("!"*60)
        return False
    
    # Test 3: Try different angles
    print("\nTest 3: Rotating to face player...")
    import math
    
    # Calculate angle to face other player
    dx = other_player.x - local_player.x
    dy = other_player.y - local_player.y
    angle_to_player = math.atan2(dy, dx)
    
    frame_facing = renderer.render(game_map, local_player.x, local_player.y, angle_to_player, other_players)
    player_chars_facing = sum(row.count('@') + row.count('O') + row.count('o') for row in frame_facing)
    
    print(f"   Angle to face player: {angle_to_player:.2f} rad")
    print(f"   Player characters visible: {player_chars_facing}")
    
    if player_chars_facing > 0:
        print("   ✅ Player visible when facing them")
    else:
        print("   ⚠️  Player not visible when facing (may be too far or behind wall)")
    
    # Test 4: Close range test
    print("\nTest 4: Close range rendering...")
    close_player = Player(local_player.x + 2.0, local_player.y, angle=3.14, player_id=3)
    frame_close = renderer.render(game_map, local_player.x, local_player.y, 0.0, [close_player])
    close_chars = sum(row.count('@') + row.count('O') + row.count('o') for row in frame_close)
    
    print(f"   Other player at ({close_player.x}, {close_player.y})")
    print(f"   Distance: 2.0 units (very close)")
    print(f"   Player characters: {close_chars}")
    
    if close_chars > 0:
        print("   ✅ Close player is visible")
        
        # Show which character is used
        if any('@' in row for row in frame_close):
            print("   📊 Using '@' character (< 2 units distance)")
        elif any('O' in row for row in frame_close):
            print("   📊 Using 'O' character (< 5 units distance)")
        elif any('o' in row for row in frame_close):
            print("   📊 Using 'o' character (< 10 units distance)")
    else:
        print("   ❌ Close player NOT visible (BUG!)")
    
    # Summary
    print("\n" + "="*60)
    print("📋 Test Summary")
    print("="*60)
    
    if has_player_chars_with and close_chars > 0:
        print("✅ ALL TESTS PASSED")
        print("✅ Player rendering is working correctly!")
        print("\nIf you still can't see players in multiplayer:")
        print("1. Make sure server is broadcasting position updates")
        print("2. Run debug server: python3 src/network/debug_server.py")
        print("3. Check that client.other_players is populated")
        return True
    else:
        print("❌ TESTS FAILED")
        print("❌ Player rendering is NOT working!")
        print("\nTo fix:")
        print("1. Check that src/renderer.py has other_players parameter")
        print("2. Check that src/game.py passes other_players to render()")
        print("3. Review MULTIPLAYER_DEBUG_GUIDE.md")
        return False

if __name__ == '__main__':
    success = test_player_rendering()
    sys.exit(0 if success else 1)
