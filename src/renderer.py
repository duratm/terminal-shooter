"""
Renderer module for Terminal Shooter.
Implements raycasting algorithm and ASCII rendering.
"""

import math
from typing import List, Tuple
from .map import Map


class Renderer:
    """Raycasting renderer for pseudo-3D first-person view."""
    
    def __init__(self, width: int = 80, height: int = 24, fov: float = math.pi / 3):
        """
        Initialize the renderer.
        
        Args:
            width: Screen width in characters
            height: Screen height in characters
            fov: Field of view in radians (default: 60 degrees)
        """
        self.width = width
        self.height = height
        self.fov = fov
        self.max_depth = 20.0  # Maximum ray distance
        
        # ASCII characters for depth shading (closest to farthest)
        self.depth_chars = ['█', '▓', '▒', '░', '·']
        self.floor_char = '·'
        self.ceiling_char = ' '
        
        # Pre-calculate ray angles for each column
        self.ray_angles = []
        for x in range(width):
            # Calculate angle for this column
            camera_x = 2 * x / width - 1  # -1 to 1
            ray_angle = camera_x * (self.fov / 2)
            self.ray_angles.append(ray_angle)
    
    def cast_ray(self, game_map: Map, x: float, y: float, angle: float) -> Tuple[float, bool]:
        """
        Cast a single ray and return distance to wall.
        
        Uses DDA (Digital Differential Analysis) algorithm.
        
        Args:
            game_map: The game map
            x: Ray origin X
            y: Ray origin Y
            angle: Ray angle in radians
            
        Returns:
            Tuple of (distance, hit_horizontal_wall)
        """
        # Ray direction
        ray_dx = math.cos(angle)
        ray_dy = math.sin(angle)
        
        # Handle zero direction
        if abs(ray_dx) < 0.0001:
            ray_dx = 0.0001
        if abs(ray_dy) < 0.0001:
            ray_dy = 0.0001
        
        # Current map tile
        map_x = int(x)
        map_y = int(y)
        
        # Length of ray from one side to next in map
        delta_dist_x = abs(1 / ray_dx) if ray_dx != 0 else 1e30
        delta_dist_y = abs(1 / ray_dy) if ray_dy != 0 else 1e30
        
        # Calculate step direction and initial side distances
        if ray_dx < 0:
            step_x = -1
            side_dist_x = (x - map_x) * delta_dist_x
        else:
            step_x = 1
            side_dist_x = (map_x + 1.0 - x) * delta_dist_x
        
        if ray_dy < 0:
            step_y = -1
            side_dist_y = (y - map_y) * delta_dist_y
        else:
            step_y = 1
            side_dist_y = (map_y + 1.0 - y) * delta_dist_y
        
        # Perform DDA
        hit = False
        side = 0  # 0 = vertical wall, 1 = horizontal wall
        max_steps = 100
        steps = 0
        
        while not hit and steps < max_steps:
            # Jump to next map square in either x or y direction
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x
                map_x += step_x
                side = 0
            else:
                side_dist_y += delta_dist_y
                map_y += step_y
                side = 1
            
            # Check if ray hit a wall
            if game_map.get_tile(map_x, map_y) == 1:
                hit = True
            
            steps += 1
        
        # Calculate distance
        if side == 0:
            distance = (map_x - x + (1 - step_x) / 2) / ray_dx
        else:
            distance = (map_y - y + (1 - step_y) / 2) / ray_dy
        
        # Prevent fish-eye effect (use perpendicular distance)
        distance = abs(distance)
        
        return (distance, side == 1)
    
    def render_column(self, distance: float, column_height: int, is_horizontal: bool) -> List[str]:
        """
        Render a single column based on distance.
        
        Args:
            distance: Distance to wall
            column_height: Height of screen in characters
            is_horizontal: True if hit horizontal wall (for shading variation)
            
        Returns:
            List of characters for the column
        """
        column = []
        
        # Calculate wall height based on distance
        if distance < 0.1:
            distance = 0.1
        
        wall_height = int(column_height / distance)
        
        # Calculate where wall starts and ends on screen
        wall_start = max(0, (column_height - wall_height) // 2)
        wall_end = min(column_height, (column_height + wall_height) // 2)
        
        # Choose character based on distance
        char_index = min(int(distance / 4), len(self.depth_chars) - 1)
        wall_char = self.depth_chars[char_index]
        
        # Horizontal walls slightly darker
        if is_horizontal and char_index < len(self.depth_chars) - 1:
            wall_char = self.depth_chars[min(char_index + 1, len(self.depth_chars) - 1)]
        
        # Build column
        for y in range(column_height):
            if y < wall_start:
                column.append(self.ceiling_char)
            elif y < wall_end:
                column.append(wall_char)
            else:
                column.append(self.floor_char)
        
        return column
    
    def render(self, game_map: Map, player_x: float, player_y: float, player_angle: float, other_players: list = None) -> List[str]:
        """
        Render the full 3D view.
        
        Args:
            game_map: The game map
            player_x: Player X position
            player_y: Player Y position
            player_angle: Player viewing angle in radians
            other_players: List of other players to render (for multiplayer)
            
        Returns:
            List of strings, one per row, representing the rendered frame
        """
        if other_players is None:
            other_players = []
        
        # Frame buffer: list of columns
        frame = [[] for _ in range(self.width)]
        
        # Cast a ray for each column
        for x in range(self.width):
            ray_angle = player_angle + self.ray_angles[x]
            wall_distance, is_horizontal = self.cast_ray(game_map, player_x, player_y, ray_angle)
            
            # Clamp distance
            wall_distance = min(wall_distance, self.max_depth)
            
            # Check for players in this ray's direction
            player_to_render = None
            player_distance = wall_distance
            
            for other_player in other_players:
                if not other_player.is_alive:
                    continue
                
                # Calculate relative position
                dx = other_player.x - player_x
                dy = other_player.y - player_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                # Skip if too far or too close
                if distance > self.max_depth or distance < 0.1:
                    continue
                
                # Calculate angle to player
                angle_to_player = math.atan2(dy, dx)
                
                # Normalize both angles to [0, 2π]
                current_ray = ray_angle % (2 * math.pi)
                target_angle = angle_to_player % (2 * math.pi)
                
                # Calculate smallest angle difference
                angle_diff = abs(current_ray - target_angle)
                if angle_diff > math.pi:
                    angle_diff = 2 * math.pi - angle_diff
                
                # Check if player is within this ray's cone
                # Each column covers about (FOV / width) radians, use 3x for overlap
                column_fov = (self.fov / self.width) * 3
                if angle_diff < column_fov and distance < player_distance:
                    player_to_render = other_player
                    player_distance = distance
            
            # Render player if found and closer than wall
            if player_to_render and player_distance < wall_distance:
                column = self.render_player_column(player_distance, self.height)
            else:
                column = self.render_column(wall_distance, self.height, is_horizontal)
            
            frame[x] = column
        
        # Convert columns to rows for display
        rows = []
        for y in range(self.height):
            row = ''.join(frame[x][y] for x in range(self.width))
            rows.append(row)
        
        return rows
    
    def render_player_column(self, distance: float, column_height: int) -> List[str]:
        """
        Render a column showing another player.
        
        Args:
            distance: Distance to the player
            column_height: Height of screen in characters
            
        Returns:
            List of characters for the column
        """
        column = []
        
        # Prevent division by zero
        if distance < 0.1:
            distance = 0.1
        
        # Calculate player height based on distance (players are "tall")
        player_height = int(column_height / (distance * 0.8))  # Slightly taller than walls
        
        # Calculate where player appears on screen
        player_start = max(0, (column_height - player_height) // 2)
        player_end = min(column_height, (column_height + player_height) // 2)
        
        # Choose character based on distance for depth perception
        if distance < 2.0:
            player_char = '@'  # Close
        elif distance < 5.0:
            player_char = 'O'  # Medium
        elif distance < 10.0:
            player_char = 'o'  # Far
        else:
            player_char = '°'  # Very far
        
        # Build column
        for y in range(column_height):
            if y < player_start:
                column.append(self.ceiling_char)
            elif y < player_end:
                column.append(player_char)
            else:
                column.append(self.floor_char)
        
        return column


if __name__ == "__main__":
    # Test the renderer
    from .map import create_default_map
    
    print("Testing raycasting renderer...")
    game_map = create_default_map()
    renderer = Renderer(width=80, height=24)
    
    # Test render from spawn point
    spawn_x, spawn_y = game_map.get_spawn_point(0)
    
    print("\nRendering view from spawn point...")
    print("(This is a static test - actual game will be animated)")
    print("=" * 80)
    
    frame = renderer.render(game_map, spawn_x, spawn_y, 0)
    for row in frame:
        print(row)
    
    print("=" * 80)
    print(f"Player position: ({spawn_x:.1f}, {spawn_y:.1f})")
    print(f"View angle: 0.0 radians (facing right)")
