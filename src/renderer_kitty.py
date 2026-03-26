import math
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw
from .renderer import Renderer
from .graphics import serialize_image_cmd, TextureManager
from .map import Map

class KittyRenderer(Renderer):
    """Renderer using Kitty graphics protocol for true-color pixel graphics."""
    
    def __init__(self, width: int = 640, height: int = 400, fov: float = math.pi / 3):
        # Initialize with pixel resolution
        super().__init__(width, height, fov)
        self.texture_manager = TextureManager()
        # Textures generated in init of TextureManager
        
        # Pre-calculate ray angles for pixel columns
        self.ray_angles = []
        for x in range(width):
            camera_x = 2 * x / width - 1
            ray_angle = camera_x * (self.fov / 2)
            self.ray_angles.append(ray_angle)
            
    def render(self, game_map: Map, player_x: float, player_y: float, 
               player_angle: float, other_players: list = None) -> Image.Image:
        """Render frame to Pillow Image."""
        if other_players is None:
            other_players = []
            
        # Create buffer
        buffer = Image.new('RGB', (self.width, self.height), color=(50, 50, 50)) # Ceiling color
        
        # Draw floor (simple)
        draw = ImageDraw.Draw(buffer)
        draw.rectangle([0, self.height//2, self.width, self.height], fill=(50, 100, 50))
        
        wall_tex = self.texture_manager.textures['wall']
        wall_tex_ns = self.texture_manager.textures['wall_ns']
        tex_w, tex_h = wall_tex.size
        
        # Raycasting loop
        for x in range(self.width):
            ray_angle = (player_angle + self.ray_angles[x])
            
            # Cast ray
            ray_dx = math.cos(ray_angle)
            ray_dy = math.sin(ray_angle)
            
            # Avoid division by zero
            if abs(ray_dx) < 1e-10: ray_dx = 1e-10
            if abs(ray_dy) < 1e-10: ray_dy = 1e-10

            map_x = int(player_x)
            map_y = int(player_y)
            
            delta_dist_x = abs(1 / ray_dx)
            delta_dist_y = abs(1 / ray_dy)
            
            step_x = 1 if ray_dx >= 0 else -1
            side_dist_x = (map_x + 1.0 - player_x) * delta_dist_x if ray_dx >= 0 else (player_x - map_x) * delta_dist_x
            
            step_y = 1 if ray_dy >= 0 else -1
            side_dist_y = (map_y + 1.0 - player_y) * delta_dist_y if ray_dy >= 0 else (player_y - map_y) * delta_dist_y
            
            hit = False
            side = 0
            
            # DDA Loop
            while not hit:
                if side_dist_x < side_dist_y:
                    side_dist_x += delta_dist_x
                    map_x += step_x
                    side = 0
                else:
                    side_dist_y += delta_dist_y
                    map_y += step_y
                    side = 1
                if game_map.get_tile(map_x, map_y) > 0:
                    hit = True
            
            # Calculate perpendicular distance to wall
            if side == 0:
                perp_wall_dist = (map_x - player_x + (1 - step_x) / 2) / ray_dx
            else:
                perp_wall_dist = (map_y - player_y + (1 - step_y) / 2) / ray_dy
            
            # Check for players in this ray direction (before wall rendering)
            player_to_render = None
            player_distance = perp_wall_dist
            
            for other in other_players:
                if not other.is_alive:
                    continue
                
                dx = other.x - player_x
                dy = other.y - player_y
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist > self.max_depth or dist < 0.1:
                    continue
                
                # Calculate angle to player
                angle_to_player = math.atan2(dy, dx)
                current_ray = ray_angle % (2 * math.pi)
                target_angle = angle_to_player % (2 * math.pi)
                
                # Calculate angle difference
                angle_diff = abs(current_ray - target_angle)
                if angle_diff > math.pi:
                    angle_diff = 2 * math.pi - angle_diff
                
                # Check if player is in this column's FOV
                column_fov = (self.fov / self.width) * 2.5  # Slightly wider for pixels
                if angle_diff < column_fov and dist < player_distance:
                    player_to_render = other
                    player_distance = dist
            
            # If a player is visible and closer than the wall, render the player
            if player_to_render and player_distance < perp_wall_dist:
                # Render player sprite
                if player_distance < 0.1:
                    player_distance = 0.1
                
                sprite_height = int(self.height / player_distance)
                y_start = (self.height - sprite_height) // 2
                y_end = y_start + sprite_height
                
                # Clamp to screen bounds
                y_start = max(0, y_start)
                y_end = min(self.height, y_end)
                
                # Draw player sprite as a colored rectangle (red for enemy)
                if y_end > y_start:
                    draw.rectangle([x, y_start, x, y_end], fill=(255, 50, 50))  # Red player
                
                continue  # Skip wall rendering for this column
                
            # Render wall (original code)
            # Wall X coordinate calculation
            if side == 0:
                wall_x_coord = player_y + perp_wall_dist * ray_dy
            else:
                wall_x_coord = player_x + perp_wall_dist * ray_dx
            
            wall_x_coord -= math.floor(wall_x_coord)
            
            # Fisheye correction (Only needed if perp_wall_dist is Euclidean, but DDA usually gives perp)
            # However, `(map_x - player_x + ...)/ray_dx` is the distance projected onto the camera plane
            # if ray_dx is cosine of ray angle relative to camera plane.
            # But here ray_dx is cosine of global angle.
            # So we DO need to correct by `cos(ray_angle - player_angle)`.
            # Wait, `(map_x - px + ...)/ray_dx` = `(dx)/cos(theta)` = `dist_euclid`.
            # No, `dx` is perpendicular to camera plane? No, dx is along X axis.
            # Standard DDA gives Euclidean distance along the ray?
            # Let's check Lodev again.
            # "perpWallDist = (sideDistX - deltaDistX)"
            # `(mapX - rayPosX + (1 - stepX) / 2) / rayDirX` is consistent.
            # "The distance projected on the camera direction... prevents fisheye."
            # So standard DDA formula DOES give corrected distance.
            # Okay, I will trust standard DDA result and NOT apply extra correction.
            
            if perp_wall_dist < 0.1: perp_wall_dist = 0.1
            
            line_height = int(self.height / perp_wall_dist)
            
            # Texture coordinate
            tex_x = int(wall_x_coord * float(tex_w))
            if side == 0 and ray_dx > 0:
                tex_x = tex_w - tex_x - 1
            if side == 1 and ray_dy < 0:
                tex_x = tex_w - tex_x - 1
                
            # Texture selection
            texture = wall_tex_ns if side == 1 else wall_tex 
            
            # Draw vertical strip
            # Scaling optimization: simple manual implementation?
            # No, Pillow resize is easiest to implement correctly.
            
            # Crop 1 pixel wide strip
            try:
                col = texture.crop((tex_x, 0, tex_x + 1, tex_h))
                col = col.resize((1, line_height), resample=Image.NEAREST)
                
                # Calculate Y position
                y_start = (self.height - line_height) // 2
                
                # Check bounds
                if y_start < 0:
                    col = col.crop((0, -y_start, 1, -y_start + self.height))
                    y_start = 0
                
                # Check if height exceeds buffer
                if y_start + col.height > self.height:
                    col = col.crop((0, 0, 1, self.height - y_start))
                    
                buffer.paste(col, (x, y_start))
            except Exception:
                pass # Ignore rendering errors for single column
        
        return buffer
