"""
Player module for Terminal Shooter.
Handles player state, movement, and actions.
"""

import math
from typing import Tuple, Optional

from .map import Map


class Player:
    """Represents a player in the game."""
    
    def __init__(self, x: float, y: float, angle: float = 0.0, player_id: int = 0):
        """
        Initialize a player.
        
        Args:
            x: Initial X position
            y: Initial Y position
            angle: Initial viewing angle in radians
            player_id: Unique player identifier
        """
        self.player_id = player_id
        
        # Position and orientation
        self.x = x
        self.y = y
        self.angle = angle
        
        # Movement
        self.move_speed = 3.0  # Units per second
        self.rot_speed = 2.0   # Radians per second
        self.collision_radius = 0.2
        
        # Health and combat
        self.max_health = 100
        self.health = self.max_health
        self.is_alive = True
        
        # Weapon state
        self.ammo = 30
        self.max_ammo = 30
        self.can_shoot = True
        self.shoot_cooldown = 0.0
        self.shoot_delay = 0.5  # Seconds between shots
        
        # Score
        self.kills = 0
        self.deaths = 0
        
        # Network (for multiplayer)
        self.last_update_time = 0.0
        
    def move(self, dx: float, dy: float, game_map: Map, delta_time: float) -> bool:
        """
        Move the player in a direction.
        
        Args:
            dx: Movement in X direction (relative to world)
            dy: Movement in Y direction (relative to world)
            game_map: Game map for collision detection
            delta_time: Time since last frame
            
        Returns:
            True if movement was successful, False if blocked by collision
        """
        # Calculate new position
        move_dist = self.move_speed * delta_time
        new_x = self.x + dx * move_dist
        new_y = self.y + dy * move_dist
        
        # Check collision
        if game_map.check_collision(new_x, new_y, self.collision_radius):
            return False
        
        # Update position
        self.x = new_x
        self.y = new_y
        return True
    
    def move_forward(self, game_map: Map, delta_time: float) -> bool:
        """Move forward in viewing direction."""
        dx = math.cos(self.angle)
        dy = math.sin(self.angle)
        return self.move(dx, dy, game_map, delta_time)
    
    def move_backward(self, game_map: Map, delta_time: float) -> bool:
        """Move backward (opposite of viewing direction)."""
        dx = -math.cos(self.angle)
        dy = -math.sin(self.angle)
        return self.move(dx, dy, game_map, delta_time)
    
    def strafe_left(self, game_map: Map, delta_time: float) -> bool:
        """Strafe left relative to viewing direction."""
        dx = math.cos(self.angle - math.pi / 2)
        dy = math.sin(self.angle - math.pi / 2)
        return self.move(dx, dy, game_map, delta_time)
    
    def strafe_right(self, game_map: Map, delta_time: float) -> bool:
        """Strafe right relative to viewing direction."""
        dx = math.cos(self.angle + math.pi / 2)
        dy = math.sin(self.angle + math.pi / 2)
        return self.move(dx, dy, game_map, delta_time)
    
    def rotate(self, delta_angle: float) -> None:
        """
        Rotate the player.
        
        Args:
            delta_angle: Angle change in radians (positive = right, negative = left)
        """
        self.angle += delta_angle
        # Normalize angle to [0, 2π)
        self.angle = self.angle % (2 * math.pi)
    
    def rotate_left(self, delta_time: float) -> None:
        """Rotate left."""
        self.rotate(-self.rot_speed * delta_time)
    
    def rotate_right(self, delta_time: float) -> None:
        """Rotate right."""
        self.rotate(self.rot_speed * delta_time)
    
    def update(self, delta_time: float) -> None:
        """
        Update player state.
        
        Args:
            delta_time: Time since last frame in seconds
        """
        # Update shoot cooldown
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= delta_time
            if self.shoot_cooldown <= 0:
                self.shoot_cooldown = 0
                self.can_shoot = True
    
    def try_shoot(self) -> bool:
        """
        Attempt to shoot.
        
        Returns:
            True if shot was fired, False if on cooldown or no ammo
        """
        if not self.can_shoot or self.ammo <= 0:
            return False
        
        self.ammo -= 1
        self.shoot_cooldown = self.shoot_delay
        self.can_shoot = False
        return True
    
    def reload(self) -> None:
        """Reload weapon to full ammo."""
        self.ammo = self.max_ammo
    
    def take_damage(self, damage: int) -> bool:
        """
        Apply damage to player.
        
        Args:
            damage: Amount of damage
            
        Returns:
            True if player died from this damage
        """
        if not self.is_alive:
            return False
        
        self.health -= damage
        
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
            self.deaths += 1
            return True
        
        return False
    
    def heal(self, amount: int) -> None:
        """
        Heal the player.
        
        Args:
            amount: Amount to heal
        """
        self.health = min(self.health + amount, self.max_health)
    
    def respawn(self, x: float, y: float, angle: float = 0.0) -> None:
        """
        Respawn the player at a location.
        
        Args:
            x: Spawn X position
            y: Spawn Y position
            angle: Spawn angle
        """
        self.x = x
        self.y = y
        self.angle = angle
        self.health = self.max_health
        self.is_alive = True
        self.ammo = self.max_ammo
        self.can_shoot = True
        self.shoot_cooldown = 0.0
    
    def get_score(self) -> int:
        """Get player's score (kills - deaths)."""
        return self.kills - self.deaths
    
    def to_dict(self) -> dict:
        """Convert player state to dictionary (for networking)."""
        return {
            'id': self.player_id,
            'x': self.x,
            'y': self.y,
            'angle': self.angle,
            'health': self.health,
            'is_alive': self.is_alive,
            'ammo': self.ammo,
            'kills': self.kills,
            'deaths': self.deaths,
        }
    
    def from_dict(self, data: dict) -> None:
        """Update player state from dictionary (for networking)."""
        self.x = data.get('x', self.x)
        self.y = data.get('y', self.y)
        self.angle = data.get('angle', self.angle)
        self.health = data.get('health', self.health)
        self.is_alive = data.get('is_alive', self.is_alive)
        self.ammo = data.get('ammo', self.ammo)
        self.kills = data.get('kills', self.kills)
        self.deaths = data.get('deaths', self.deaths)
    
    def __repr__(self) -> str:
        """String representation of player."""
        status = "alive" if self.is_alive else "dead"
        return f"Player {self.player_id} at ({self.x:.1f}, {self.y:.1f}) - {status} - HP:{self.health} K:{self.kills} D:{self.deaths}"


if __name__ == "__main__":
    # Test player module
    from .map import create_default_map
    
    print("Testing Player class...")
    game_map = create_default_map()
    spawn_x, spawn_y = game_map.get_spawn_point(0)
    
    player = Player(spawn_x, spawn_y, 0.0, player_id=1)
    print(f"Created: {player}")
    
    # Test movement
    print("\nTesting movement...")
    player.move_forward(game_map, 1.0)
    print(f"After forward: {player}")
    
    player.rotate_right(0.5)
    print(f"After rotating right: angle = {math.degrees(player.angle):.1f}°")
    
    # Test shooting
    print("\nTesting shooting...")
    print(f"Ammo before: {player.ammo}")
    success = player.try_shoot()
    print(f"Shot fired: {success}, Ammo after: {player.ammo}")
    
    # Test damage
    print("\nTesting damage...")
    print(f"Health: {player.health}")
    player.take_damage(30)
    print(f"After 30 damage: {player.health}")
    player.take_damage(80)
    print(f"After 80 more damage: {player.health}, Alive: {player.is_alive}")
    
    # Test respawn
    print("\nTesting respawn...")
    player.respawn(spawn_x, spawn_y)
    print(f"After respawn: {player}")
    
    # Test serialization
    print("\nTesting serialization...")
    data = player.to_dict()
    print(f"Serialized: {data}")
