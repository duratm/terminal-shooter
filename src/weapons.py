"""
Weapons module for Terminal Shooter.
Handles weapons, projectiles, and combat mechanics.
"""

import math
import time
from typing import List, Tuple, Optional

from .map import Map


class Projectile:
    """Represents a projectile (bullet) in the game."""
    
    def __init__(self, x: float, y: float, angle: float, damage: int = 25, speed: float = 10.0, max_distance: float = 20.0):
        """
        Initialize a projectile.
        
        Args:
            x: Starting X position
            y: Starting Y position
            angle: Direction angle in radians
            damage: Damage dealt on hit
            speed: Movement speed (units per second)
            max_distance: Maximum travel distance before despawning
        """
        self.x = x
        self.y = y
        self.start_x = x
        self.start_y = y
        self.angle = angle
        self.damage = damage
        self.speed = speed
        self.max_distance = max_distance
        
        self.velocity_x = math.cos(angle) * speed
        self.velocity_y = math.sin(angle) * speed
        
        self.active = True
        self.shooter_id = None  # ID of player who shot this
    
    def update(self, delta_time: float, game_map: Map) -> None:
        """
        Update projectile position.
        
        Args:
            delta_time: Time since last frame
            game_map: Game map for collision detection
        """
        if not self.active:
            return
        
        # Move projectile
        self.x += self.velocity_x * delta_time
        self.y += self.velocity_y * delta_time
        
        # Check wall collision
        if game_map.is_wall(self.x, self.y):
            self.active = False
            return
        
        # Check max distance
        dist = math.sqrt((self.x - self.start_x)**2 + (self.y - self.start_y)**2)
        if dist >= self.max_distance:
            self.active = False
    
    def check_hit(self, target_x: float, target_y: float, hit_radius: float = 0.3) -> bool:
        """
        Check if projectile hits a target.
        
        Args:
            target_x: Target X position
            target_y: Target Y position
            hit_radius: Hit detection radius
            
        Returns:
            True if hit detected
        """
        if not self.active:
            return False
        
        dist = math.sqrt((self.x - target_x)**2 + (self.y - target_y)**2)
        return dist <= hit_radius
    
    def to_dict(self) -> dict:
        """Convert to dictionary for networking."""
        return {
            'x': self.x,
            'y': self.y,
            'angle': self.angle,
            'active': self.active,
            'shooter_id': self.shooter_id,
        }


class Weapon:
    """Base weapon class."""
    
    def __init__(self, name: str = "Rifle", damage: int = 25, fire_rate: float = 2.0, 
                 max_ammo: int = 30, projectile_speed: float = 15.0, max_range: float = 20.0):
        """
        Initialize a weapon.
        
        Args:
            name: Weapon name
            damage: Damage per shot
            fire_rate: Shots per second
            max_ammo: Maximum ammo capacity
            projectile_speed: Speed of projectiles
            max_range: Maximum projectile range
        """
        self.name = name
        self.damage = damage
        self.fire_rate = fire_rate
        self.fire_delay = 1.0 / fire_rate
        self.max_ammo = max_ammo
        self.projectile_speed = projectile_speed
        self.max_range = max_range
    
    def create_projectile(self, x: float, y: float, angle: float, shooter_id: Optional[int] = None) -> Projectile:
        """
        Create a projectile from this weapon.
        
        Args:
            x: Starting position X
            y: Starting position Y
            angle: Shooting angle
            shooter_id: ID of shooter
            
        Returns:
            New projectile instance
        """
        projectile = Projectile(x, y, angle, self.damage, self.projectile_speed, self.max_range)
        projectile.shooter_id = shooter_id
        return projectile


class WeaponManager:
    """Manages projectiles and hit detection."""
    
    def __init__(self):
        """Initialize weapon manager."""
        self.projectiles: List[Projectile] = []
        self.hit_markers: List[Tuple[float, float, float]] = []  # (x, y, timestamp)
        self.hit_marker_duration = 0.5  # seconds
    
    def add_projectile(self, projectile: Projectile) -> None:
        """Add a projectile to track."""
        self.projectiles.append(projectile)
    
    def shoot(self, weapon: Weapon, x: float, y: float, angle: float, shooter_id: Optional[int] = None) -> Projectile:
        """
        Fire a weapon and create projectile.
        
        Args:
            weapon: Weapon to fire
            x: Shooter position X
            y: Shooter position Y
            angle: Shooting angle
            shooter_id: ID of shooter
            
        Returns:
            Created projectile
        """
        projectile = weapon.create_projectile(x, y, angle, shooter_id)
        self.add_projectile(projectile)
        return projectile
    
    def update(self, delta_time: float, game_map: Map) -> None:
        """
        Update all projectiles.
        
        Args:
            delta_time: Time since last frame
            game_map: Game map
        """
        # Update projectiles
        for projectile in self.projectiles:
            projectile.update(delta_time, game_map)
        
        # Remove inactive projectiles
        self.projectiles = [p for p in self.projectiles if p.active]
        
        # Update hit markers
        current_time = time.time()
        self.hit_markers = [(x, y, t) for x, y, t in self.hit_markers 
                           if current_time - t < self.hit_marker_duration]
    
    def check_hits(self, player_x: float, player_y: float, player_id: int, hit_radius: float = 0.3) -> List[Projectile]:
        """
        Check if any projectiles hit a player.
        
        Args:
            player_x: Player position X
            player_y: Player position Y
            player_id: Player ID (projectiles from this player are ignored)
            hit_radius: Hit detection radius
            
        Returns:
            List of projectiles that hit
        """
        hits = []
        
        for projectile in self.projectiles:
            # Don't hit your own projectiles
            if projectile.shooter_id == player_id:
                continue
            
            if projectile.check_hit(player_x, player_y, hit_radius):
                hits.append(projectile)
                projectile.active = False
                
                # Add hit marker
                self.hit_markers.append((player_x, player_y, time.time()))
        
        return hits
    
    def get_active_projectiles(self) -> List[Projectile]:
        """Get list of all active projectiles."""
        return [p for p in self.projectiles if p.active]
    
    def clear(self) -> None:
        """Clear all projectiles."""
        self.projectiles.clear()
        self.hit_markers.clear()


# Pre-defined weapons
WEAPON_RIFLE = Weapon(
    name="Rifle",
    damage=25,
    fire_rate=2.0,
    max_ammo=30,
    projectile_speed=15.0,
    max_range=20.0
)

WEAPON_PISTOL = Weapon(
    name="Pistol",
    damage=15,
    fire_rate=3.0,
    max_ammo=15,
    projectile_speed=12.0,
    max_range=15.0
)

WEAPON_SHOTGUN = Weapon(
    name="Shotgun",
    damage=50,
    fire_rate=0.8,
    max_ammo=8,
    projectile_speed=10.0,
    max_range=8.0
)


if __name__ == "__main__":
    # Test weapons module
    from .map import create_default_map
    
    print("Testing weapons and projectiles...")
    game_map = create_default_map()
    weapon_mgr = WeaponManager()
    
    # Create projectile
    print("\nCreating projectile...")
    projectile = weapon_mgr.shoot(WEAPON_RIFLE, 5.0, 5.0, 0.0, shooter_id=1)
    print(f"Projectile at ({projectile.x:.1f}, {projectile.y:.1f}), active: {projectile.active}")
    
    # Simulate movement
    print("\nSimulating movement...")
    for i in range(5):
        weapon_mgr.update(0.1, game_map)
        active_proj = weapon_mgr.get_active_projectiles()
        if active_proj:
            p = active_proj[0]
            print(f"Frame {i+1}: Projectile at ({p.x:.1f}, {p.y:.1f})")
    
    # Test hit detection
    print("\nTesting hit detection...")
    projectile2 = weapon_mgr.shoot(WEAPON_RIFLE, 10.0, 10.0, 0.0, shooter_id=1)
    weapon_mgr.update(0.1, game_map)
    
    # Check if it hits target
    target_x, target_y = 10.5, 10.0
    hits = weapon_mgr.check_hits(target_x, target_y, player_id=2)
    print(f"Checking hit at ({target_x}, {target_y}): {len(hits)} hits")
    
    print("\nWeapon stats:")
    for weapon in [WEAPON_RIFLE, WEAPON_PISTOL, WEAPON_SHOTGUN]:
        print(f"  {weapon.name}: {weapon.damage} dmg, {weapon.fire_rate:.1f} rps, {weapon.max_ammo} ammo")
