"""
HUD (Heads-Up Display) module for Terminal Shooter.
Displays health, ammo, score, and other game information.
"""

import math
from typing import List, Optional


class HUD:
    """Manages the heads-up display."""
    
    def __init__(self, width: int, height: int):
        """
        Initialize HUD.
        
        Args:
            width: Screen width
            height: Screen height
        """
        self.width = width
        self.height = height
        self.minimap_size = 15  # Size of minimap
        self.show_minimap = True
        self.messages: List[tuple] = []  # (message, timestamp)
        self.message_duration = 3.0  # seconds
    
    def render_health_bar(self, health: int, max_health: int, width: int = 20) -> str:
        """
        Render a health bar.
        
        Args:
            health: Current health
            max_health: Maximum health
            width: Width of bar in characters
            
        Returns:
            String representation of health bar
        """
        health = max(0, min(health, max_health))
        filled = int((health / max_health) * width)
        empty = width - filled
        
        bar = '█' * filled + '░' * empty
        return f"HP:[{bar}] {health}/{max_health}"
    
    def render_ammo_display(self, ammo: int, max_ammo: int) -> str:
        """
        Render ammo display.
        
        Args:
            ammo: Current ammo
            max_ammo: Maximum ammo
            
        Returns:
            String representation of ammo
        """
        return f"AMMO:[{ammo:2d}/{max_ammo:2d}]"
    
    def render_score_display(self, kills: int, deaths: int) -> str:
        """
        Render score display.
        
        Args:
            kills: Number of kills
            deaths: Number of deaths
            
        Returns:
            String representation of score
        """
        score = kills - deaths
        return f"K/D:{kills}/{deaths} ({score:+d})"
    
    def render_crosshair(self, width: int, height: int) -> List[tuple]:
        """
        Get crosshair positions.
        
        Args:
            width: Screen width
            height: Screen height
            
        Returns:
            List of (x, y, char) tuples for crosshair
        """
        center_x = width // 2
        center_y = height // 2
        
        crosshair = [
            (center_x, center_y, '+'),
            (center_x - 1, center_y, '-'),
            (center_x + 1, center_y, '-'),
            (center_x, center_y - 1, '|'),
            (center_x, center_y + 1, '|'),
        ]
        
        return crosshair
    
    def render_minimap(self, game_map, player_x: float, player_y: float, 
                       other_players: Optional[List] = None) -> List[str]:
        """
        Render a minimap.
        
        Args:
            game_map: The game map
            player_x: Player X position
            player_y: Player Y position
            other_players: List of other players (optional)
            
        Returns:
            List of strings representing minimap lines
        """
        if not self.show_minimap:
            return []
        
        minimap = []
        size = self.minimap_size
        
        # Calculate visible area
        tile_x = int(player_x)
        tile_y = int(player_y)
        radius = size // 2
        
        for dy in range(-radius, radius + 1):
            row = []
            for dx in range(-radius, radius + 1):
                map_x = tile_x + dx
                map_y = tile_y + dy
                
                # Check if this is player position
                if dx == 0 and dy == 0:
                    row.append('@')
                # Check for other players
                elif other_players:
                    found_player = False
                    for p in other_players:
                        if int(p.x) == map_x and int(p.y) == map_y:
                            row.append('P')
                            found_player = True
                            break
                    if not found_player:
                        tile = game_map.get_tile(map_x, map_y)
                        row.append('#' if tile == 1 else '.')
                else:
                    tile = game_map.get_tile(map_x, map_y)
                    row.append('#' if tile == 1 else '.')
            
            minimap.append(''.join(row))
        
        return minimap
    
    def add_message(self, message: str, timestamp: float) -> None:
        """
        Add a temporary message to display.
        
        Args:
            message: Message text
            timestamp: Current time
        """
        self.messages.append((message, timestamp))
    
    def get_active_messages(self, current_time: float) -> List[str]:
        """
        Get currently active messages.
        
        Args:
            current_time: Current time
            
        Returns:
            List of active messages
        """
        # Filter expired messages
        self.messages = [(msg, t) for msg, t in self.messages 
                        if current_time - t < self.message_duration]
        
        # Return just the message text
        return [msg for msg, _ in self.messages[-3:]]  # Show last 3 messages
    
    def render_status_line(self, player, fps: int, additional_info: str = "") -> str:
        """
        Render the status line with all info.
        
        Args:
            player: Player object
            fps: Current FPS
            additional_info: Additional information to display
            
        Returns:
            Status line string
        """
        health_bar = self.render_health_bar(player.health, player.max_health, 15)
        ammo = self.render_ammo_display(player.ammo, player.max_ammo)
        score = self.render_score_display(player.kills, player.deaths)
        pos = f"({player.x:.1f},{player.y:.1f})"
        angle = f"{math.degrees(player.angle):.0f}°"
        
        parts = [health_bar, ammo, score, f"POS:{pos}", f"ANG:{angle}", f"FPS:{fps}"]
        
        if additional_info:
            parts.append(additional_info)
        
        return " | ".join(parts)


if __name__ == "__main__":
    # Test HUD module
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from player import Player
    from map import create_default_map
    import time
    
    print("Testing HUD...")
    game_map = create_default_map()
    hud = HUD(width=80, height=24)
    
    player = Player(10.5, 10.5, 0.0, player_id=1)
    
    # Test health bar
    print("\nHealth bars:")
    print(hud.render_health_bar(100, 100))
    print(hud.render_health_bar(50, 100))
    print(hud.render_health_bar(10, 100))
    
    # Test ammo
    print("\nAmmo display:")
    print(hud.render_ammo_display(30, 30))
    print(hud.render_ammo_display(5, 30))
    
    # Test score
    print("\nScore display:")
    print(hud.render_score_display(10, 3))
    print(hud.render_score_display(5, 8))
    
    # Test status line
    print("\nStatus line:")
    status = hud.render_status_line(player, 60)
    print(status)
    
    # Test minimap
    print("\nMinimap:")
    minimap = hud.render_minimap(game_map, player.x, player.y)
    for line in minimap:
        print(line)
    
    # Test messages
    print("\nMessages:")
    current_time = time.time()
    hud.add_message("You killed Player 2!", current_time)
    hud.add_message("Ammo low!", current_time)
    messages = hud.get_active_messages(current_time)
    for msg in messages:
        print(f"  > {msg}")
    
    # Test crosshair
    print("\nCrosshair positions:")
    crosshair = hud.render_crosshair(80, 24)
    for x, y, char in crosshair:
        print(f"  ({x}, {y}): '{char}'")
