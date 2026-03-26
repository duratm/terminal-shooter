import io
import base64
from PIL import Image, ImageDraw, ImageColor
import random

def serialize_image_cmd(image: Image.Image, z_index: int = 0, quiet: int = 2, cols: int = 0, rows: int = 0, img_id: int = 0) -> str:
    """Serialize PIL Image to Kitty graphics protocol command."""
    # Use raw RGB/RGBA format for speed (avoids PNG compression)
    if image.mode == 'RGB':
        fmt = 24
    elif image.mode == 'RGBA':
        fmt = 32
    else:
        # Fallback for other modes
        image = image.convert('RGB')
        fmt = 24
        
    raw_data = image.tobytes()
    b64_data = base64.standard_b64encode(raw_data).decode('ascii')
    
    res = []
    
    while b64_data:
        chunk, b64_data = b64_data[:4096], b64_data[4096:]
        m = 1 if b64_data else 0
        
        # Build command keys
        cmd = {}
        if not res: # First chunk needs metadata
            # a=T (transmit), f=fmt (24=RGB, 32=RGBA), q=quiet, z=z_index
            # s=width, v=height (required for raw formats)
            cmd = {
                'a': 'T', 
                'f': fmt, 
                's': image.width,
                'v': image.height,
                'm': m, 
                'q': quiet, 
                'z': z_index, 
                'C': 1
            }
            
            # Add scaling if provided
            if cols > 0: cmd['c'] = cols
            if rows > 0: cmd['r'] = rows
            
            # Add image ID if provided
            if img_id > 0: cmd['i'] = img_id
            
        else:
            cmd = {'m': m} # Subsequent chunks just need m flag
            
        vals = ','.join(f'{k}={v}' for k, v in cmd.items())
        res.append(f'\033_G{vals};{chunk}\033\\')
    
    return ''.join(res)

class TextureManager:
    def __init__(self):
        self.textures = {}
        self.generate_default_textures()
    
    def generate_default_textures(self):
        # Wall Texture (Brick pattern)
        wall_size = 64
        wall = Image.new('RGB', (wall_size, wall_size), color=(150, 75, 0)) # Brownish
        d = ImageDraw.Draw(wall)
        # Bricks
        for y in range(0, wall_size, 16):
            offset = 0 if (y // 16) % 2 == 0 else 8
            for x in range(0, wall_size, 16):
                d.rectangle([x + offset, y, x + offset + 14, y + 14], fill=(180, 90, 20), outline=(100, 50, 0))
        self.textures['wall'] = wall
        
        # Wall N/S (Slightly darker)
        self.textures['wall_ns'] = Image.eval(wall, lambda x: x * 0.8)

        # Floor (Noise/Grass)
        floor = Image.new('RGB', (wall_size, wall_size), color=(50, 100, 50))
        pixels = floor.load()
        for i in range(wall_size):
            for j in range(wall_size):
                r = random.randint(-10, 10)
                pixels[i, j] = (50+r, 100+r, 50+r)
        self.textures['floor'] = floor

        # Ceiling (Sky)
        # We don't really texture map ceiling in simple raycasters usually, just solid color
        # But we can provide a texture if needed
        
        # Player Sprite
        player = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(player)
        d.ellipse([16, 8, 48, 40], fill=(200, 50, 50)) # Head
        d.rectangle([16, 40, 48, 64], fill=(50, 50, 200)) # Body
        self.textures['player'] = player
        
    def get_texture(self, name):
        return self.textures.get(name)
