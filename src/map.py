"""
Map module for Terminal Shooter.
Handles map data, loading, and collision detection.
"""

import os
from typing import List, Tuple, Optional


class Map:
    """Represents a game map with walls and collision detection."""
    
    def __init__(self, width: int = 24, height: int = 24):
        """
        Initialize a map.
        
        Args:
            width: Map width in tiles
            height: Map height in tiles
        """
        self.width = width
        self.height = height
        self.tiles: List[List[int]] = []
        self.spawn_points: List[Tuple[float, float]] = []
        
    def load_from_string(self, map_data: str) -> None:
        """
        Load map from a string representation.
        
        Map format:
        - '#' or '1' = wall
        - ' ' or '0' = empty space
        - 'S' = spawn point
        
        Args:
            map_data: String representation of the map
        """
        lines = [line.rstrip() for line in map_data.strip().split('\n')]
        self.height = len(lines)
        self.width = max(len(line) for line in lines) if lines else 0
        
        self.tiles = []
        self.spawn_points = []
        
        for y, line in enumerate(lines):
            row = []
            for x, char in enumerate(line.ljust(self.width)):
                if char in ('#', '1'):
                    row.append(1)  # Wall
                elif char == 'S':
                    row.append(0)  # Empty space
                    self.spawn_points.append((x + 0.5, y + 0.5))  # Center of tile
                else:
                    row.append(0)  # Empty space
            self.tiles.append(row)
    
    def load_from_file(self, filepath: str) -> None:
        """
        Load map from a file.
        
        Args:
            filepath: Path to the map file
        """
        with open(filepath, 'r') as f:
            map_data = f.read()
        self.load_from_string(map_data)
    
    def get_tile(self, x: int, y: int) -> int:
        """
        Get the tile value at coordinates.
        
        Args:
            x: X coordinate (tile)
            y: Y coordinate (tile)
            
        Returns:
            Tile value (0 = empty, 1 = wall) or 1 if out of bounds
        """
        if not self.is_valid_tile(x, y):
            return 1  # Treat out of bounds as wall
        return self.tiles[y][x]
    
    def is_valid_tile(self, x: int, y: int) -> bool:
        """
        Check if tile coordinates are valid.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if coordinates are within map bounds
        """
        return 0 <= x < self.width and 0 <= y < self.height
    
    def is_wall(self, x: float, y: float) -> bool:
        """
        Check if a position collides with a wall.
        
        Args:
            x: X position (world coordinates)
            y: Y position (world coordinates)
            
        Returns:
            True if position is inside a wall
        """
        tile_x = int(x)
        tile_y = int(y)
        return self.get_tile(tile_x, tile_y) == 1
    
    def check_collision(self, x: float, y: float, radius: float = 0.2) -> bool:
        """
        Check collision with walls using a circular hitbox.
        
        Args:
            x: X position (world coordinates)
            y: Y position (world coordinates)
            radius: Collision radius
            
        Returns:
            True if position collides with any wall
        """
        # Check 4 points around the player (simplified collision)
        offsets = [
            (radius, 0),
            (-radius, 0),
            (0, radius),
            (0, -radius)
        ]
        
        for dx, dy in offsets:
            if self.is_wall(x + dx, y + dy):
                return True
        
        return False
    
    def get_spawn_point(self, index: int = 0) -> Tuple[float, float]:
        """
        Get a spawn point by index.
        
        Args:
            index: Spawn point index
            
        Returns:
            Tuple of (x, y) coordinates, or (1.5, 1.5) if no spawn points
        """
        if not self.spawn_points:
            return (1.5, 1.5)  # Default spawn
        
        index = index % len(self.spawn_points)
        return self.spawn_points[index]
    
    def __str__(self) -> str:
        """String representation of the map."""
        result = []
        for row in self.tiles:
            result.append(''.join('#' if tile == 1 else ' ' for tile in row))
        return '\n'.join(result)


def create_default_map() -> Map:
    """Create a default arena map for testing."""
    map_data = """
########################
#                      #
#  S                   #
#                      #
#      ####    ####    #
#      #        #      #
#                      #
#                      #
#      #        #      #
#      ####    ####    #
#                      #
#                      #
#                      #
#                      #
#      ####    ####    #
#      #        #      #
#                      #
#                      #
#      #        #      #
#      ####    ####    #
#                   S  #
#                      #
########################
"""
    
    game_map = Map()
    game_map.load_from_string(map_data)
    return game_map


if __name__ == "__main__":
    # Test the map module
    print("Creating default map...")
    game_map = create_default_map()
    print(f"Map size: {game_map.width}x{game_map.height}")
    print(f"Spawn points: {len(game_map.spawn_points)}")
    print("\nMap preview:")
    print(game_map)
    print(f"\nSpawn point 0: {game_map.get_spawn_point(0)}")
    print(f"Spawn point 1: {game_map.get_spawn_point(1)}")
    print(f"Wall at (0, 0): {game_map.is_wall(0.5, 0.5)}")
    print(f"Wall at (2, 2): {game_map.is_wall(2.5, 2.5)}")
