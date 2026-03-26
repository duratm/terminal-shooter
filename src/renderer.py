"""
Renderer module for Terminal Shooter.
Implements raycasting algorithm with clean, visible ASCII rendering.
"""

import math
import curses
from typing import List, Tuple, Optional
from .map import Map


# Color constants (indices for curses color pairs)
COLOR_WALL_BRIGHT = 1
COLOR_WALL_MEDIUM = 2
COLOR_WALL_DIM = 3
COLOR_FLOOR = 5
COLOR_CEILING = 6
COLOR_PLAYER = 7
COLOR_CROSSHAIR = 8
COLOR_HUD = 9
COLOR_HEALTH_HIGH = 10
COLOR_HEALTH_MED = 11
COLOR_HEALTH_LOW = 12


def init_colors():
    """Initialize curses color pairs for the game."""
    try:
        curses.start_color()
        curses.use_default_colors()
        
        # Wall colors - high contrast gradient
        curses.init_pair(COLOR_WALL_BRIGHT, curses.COLOR_WHITE, curses.COLOR_WHITE)
        curses.init_pair(COLOR_WALL_MEDIUM, curses.COLOR_WHITE, -1)
        curses.init_pair(COLOR_WALL_DIM, curses.COLOR_CYAN, -1)
        
        # Environment
        curses.init_pair(COLOR_FLOOR, curses.COLOR_GREEN, -1)
        curses.init_pair(COLOR_CEILING, curses.COLOR_BLUE, -1)
        
        # Players - bright red for visibility
        curses.init_pair(COLOR_PLAYER, curses.COLOR_RED, -1)
        
        # HUD
        curses.init_pair(COLOR_CROSSHAIR, curses.COLOR_YELLOW, -1)
        curses.init_pair(COLOR_HUD, curses.COLOR_WHITE, -1)
        curses.init_pair(COLOR_HEALTH_HIGH, curses.COLOR_GREEN, -1)
        curses.init_pair(COLOR_HEALTH_MED, curses.COLOR_YELLOW, -1)
        curses.init_pair(COLOR_HEALTH_LOW, curses.COLOR_RED, -1)
        
        return True
    except curses.error:
        return False


class Renderer:
    """Raycasting renderer with clean, high-visibility ASCII graphics."""
    
    def __init__(self, width: int = 80, height: int = 24, fov: float = math.pi / 3):
        """Initialize the renderer."""
        self.width = width
        self.height = height
        self.fov = fov
        self.max_depth = 20.0
        
        # Simple, clean wall characters - solid blocks for best visibility
        # Ordered from closest (brightest) to farthest (darkest)
        self.wall_shades = ['█', '█', '▓', '▒', '░']
        
        # Simple floor and ceiling
        self.floor_char = '.'
        self.ceiling_char = ' '
        
        # Pre-calculate ray angles
        self.ray_angles = []
        for x in range(width):
            camera_x = 2 * x / width - 1
            ray_angle = camera_x * (self.fov / 2)
            self.ray_angles.append(ray_angle)
        
        self.colors_enabled = False
    
    def enable_colors(self):
        """Enable color rendering."""
        self.colors_enabled = init_colors()
        return self.colors_enabled
    
    def cast_ray(self, game_map: Map, x: float, y: float, angle: float) -> Tuple[float, bool]:
        """Cast a ray and return distance to wall using DDA algorithm."""
        ray_dx = math.cos(angle)
        ray_dy = math.sin(angle)
        
        if abs(ray_dx) < 0.0001:
            ray_dx = 0.0001
        if abs(ray_dy) < 0.0001:
            ray_dy = 0.0001
        
        map_x = int(x)
        map_y = int(y)
        
        delta_dist_x = abs(1 / ray_dx) if ray_dx != 0 else 1e30
        delta_dist_y = abs(1 / ray_dy) if ray_dy != 0 else 1e30
        
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
        
        hit = False
        side = 0
        
        for _ in range(100):
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x
                map_x += step_x
                side = 0
            else:
                side_dist_y += delta_dist_y
                map_y += step_y
                side = 1
            
            if game_map.get_tile(map_x, map_y) >= 1:
                hit = True
                break
        
        if side == 0:
            distance = (map_x - x + (1 - step_x) / 2) / ray_dx
        else:
            distance = (map_y - y + (1 - step_y) / 2) / ray_dy
        
        return (abs(distance), side == 1)
    
    def get_wall_shade(self, distance: float, is_side_wall: bool) -> Tuple[str, int]:
        """Get wall character and color based on distance."""
        # Calculate shade index based on distance
        if distance < 3.0:
            shade_idx = 0
            color = COLOR_WALL_BRIGHT
        elif distance < 6.0:
            shade_idx = 1
            color = COLOR_WALL_MEDIUM
        elif distance < 10.0:
            shade_idx = 2
            color = COLOR_WALL_MEDIUM
        elif distance < 15.0:
            shade_idx = 3
            color = COLOR_WALL_DIM
        else:
            shade_idx = 4
            color = COLOR_WALL_DIM
        
        # Side walls (N/S facing) are slightly darker for 3D effect
        # This is a standard raycasting technique to distinguish corners
        if is_side_wall and shade_idx < len(self.wall_shades) - 1:
            shade_idx += 1
        
        return self.wall_shades[shade_idx], color
    
    def render_column(self, distance: float, is_side_wall: bool, col_idx: int) -> List[Tuple[str, int]]:
        """Render a single column with clean graphics."""
        column = []
        
        # Prevent division by zero
        if distance < 0.1:
            distance = 0.1
        
        # Calculate wall height (taller walls when closer)
        wall_height = int(self.height / distance)
        
        # Calculate wall position on screen
        wall_start = max(0, (self.height - wall_height) // 2)
        wall_end = min(self.height, (self.height + wall_height) // 2)
        
        # Get wall appearance
        wall_char, wall_color = self.get_wall_shade(distance, is_side_wall)
        
        # Build the column
        for y in range(self.height):
            if y < wall_start:
                # Ceiling - empty space
                column.append((self.ceiling_char, COLOR_CEILING))
            elif y < wall_end:
                # Wall - solid block
                column.append((wall_char, wall_color))
            else:
                # Floor - simple dots
                column.append((self.floor_char, COLOR_FLOOR))
        
        return column
    
    def render_player_column(self, distance: float) -> List[Tuple[str, int]]:
        """Render a column showing another player - simple and visible."""
        column = []
        
        if distance < 0.1:
            distance = 0.1
        
        # Player height on screen
        player_height = int(self.height / (distance * 0.7))
        player_start = max(0, (self.height - player_height) // 2)
        player_end = min(self.height, (self.height + player_height) // 2)
        
        # Simple player character based on distance
        if distance < 3.0:
            player_char = '█'
        elif distance < 7.0:
            player_char = '▓'
        elif distance < 12.0:
            player_char = '●'
        else:
            player_char = '○'
        
        for y in range(self.height):
            if y < player_start:
                column.append((self.ceiling_char, COLOR_CEILING))
            elif y < player_end:
                column.append((player_char, COLOR_PLAYER))
            else:
                column.append((self.floor_char, COLOR_FLOOR))
        
        return column
    
    def render(self, game_map: Map, player_x: float, player_y: float, 
               player_angle: float, other_players: list = None) -> List[List[Tuple[str, int]]]:
        """Render the full 3D view."""
        if other_players is None:
            other_players = []
        
        frame = [[] for _ in range(self.width)]
        
        for x in range(self.width):
            ray_angle = player_angle + self.ray_angles[x]
            wall_distance, is_side_wall = self.cast_ray(game_map, player_x, player_y, ray_angle)
            wall_distance = min(wall_distance, self.max_depth)
            
            # Check for players in this ray direction
            player_to_render = None
            player_distance = wall_distance
            
            for other in other_players:
                if not other.is_alive:
                    continue
                
                dx = other.x - player_x
                dy = other.y - player_y
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist > self.max_depth or dist < 0.1:
                    continue
                
                angle_to_player = math.atan2(dy, dx)
                current_ray = ray_angle % (2 * math.pi)
                target_angle = angle_to_player % (2 * math.pi)
                
                angle_diff = abs(current_ray - target_angle)
                if angle_diff > math.pi:
                    angle_diff = 2 * math.pi - angle_diff
                
                column_fov = (self.fov / self.width) * 3
                if angle_diff < column_fov and dist < player_distance:
                    player_to_render = other
                    player_distance = dist
            
            # Render the column
            if player_to_render and player_distance < wall_distance:
                frame[x] = self.render_player_column(player_distance)
            else:
                frame[x] = self.render_column(wall_distance, is_side_wall, x)
        
        return frame
    
    def render_to_strings(self, game_map: Map, player_x: float, player_y: float,
                          player_angle: float, other_players: list = None) -> List[str]:
        """Render to plain strings (no colors)."""
        frame = self.render(game_map, player_x, player_y, player_angle, other_players)
        
        rows = []
        for y in range(self.height):
            row = ''.join(frame[x][y][0] for x in range(self.width))
            rows.append(row)
        
        return rows
