"""
Game module - Main game loop and state management.
"""

import curses
import time
import sys
import math
from typing import Optional, List
import threading
from src.input_evdev import EvdevController

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError as e:
    with open("kitty_debug.log", "a") as f:
        import traceback
        f.write(f"ImportError: {e}\n")
        traceback.print_exc(file=f)
    PYNPUT_AVAILABLE = False
except Exception as e:
    # Log error
    with open("kitty_debug.log", "a") as f:
        import traceback
        f.write(f"Exception: {e}\n")
        traceback.print_exc(file=f)
    PYNPUT_AVAILABLE = False

from .map import Map, create_default_map
from .renderer import Renderer, init_colors, COLOR_CROSSHAIR, COLOR_HUD, COLOR_HEALTH_HIGH, COLOR_HEALTH_MED, COLOR_HEALTH_LOW, COLOR_PLAYER, COLOR_WALL_DIM
from .renderer_kitty import KittyRenderer
from .graphics import serialize_image_cmd
from .player import Player
from .weapons import WeaponManager, WEAPON_RIFLE
from .ui.hud import HUD
from .network.client import GameClient


class Game:
    """Main game class managing the game loop and state."""
    
    def __init__(self, stdscr, game_map: Optional[Map] = None, client: Optional[GameClient] = None, sensitivity: float = 0.15, graphics_mode: str = 'ascii', native_input: bool = False, use_evdev: bool = False):
        """
        Initialize the game.
        
        Args:
            stdscr: Curses standard screen object
            game_map: Game map (creates default if None)
            client: Network client for multiplayer (None for solo)
            sensitivity: Mouse sensitivity (default 0.15)
            graphics_mode: 'ascii' or 'kitty'
            native_input: Whether to try using pynput for native input
            use_evdev: Whether to use evdev for input (Wayland/console)
        """
        self.stdscr = stdscr
        self.running = True
        self.client = client  # Network client for multiplayer
        self.is_multiplayer = client is not None
        self.graphics_mode = graphics_mode
        
        # Initialize curses
        try:
            curses.curs_set(0)  # Hide cursor
        except curses.error:
            pass  # Some terminals don't support cursor visibility control
        curses.noecho()
        stdscr.nodelay(1)  # Non-blocking input
        stdscr.keypad(1)
        
        # Initialize colors
        self.colors_enabled = init_colors()
        
        # Enable mouse support
        curses.mouseinterval(0)  # No click delay
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        # Enable mouse movement tracking (SGR mode for better terminal support)
        print('\033[?1003h', end='', flush=True)  # Enable mouse tracking
        
        # Enable Kitty Keyboard Protocol (if supported) to get KeyUp events
        # We request flags=2 (report event types) to get release events
        # CSI > 1 u is standard enable command but we want CSI = 2 u to set flags
        if self.graphics_mode == 'kitty':
            sys.stdout.write('\033[>1u') # Request enabled
            sys.stdout.write('\033[=2u') # Request release events
            sys.stdout.flush()
        
        # Get screen dimensions
        self.screen_height, self.screen_width = stdscr.getmaxyx()
        
        # Create map and renderer
        self.game_map = game_map if game_map else create_default_map()
        
        if self.graphics_mode == 'kitty':
            # Use lower resolution for performance (160x100)
            # 320x200 can be laggy due to large payload size per frame
            # 160x100 is much faster and still looks okay with scaling
            self.renderer = KittyRenderer(width=160, height=100)
        else:
            self.renderer = Renderer(width=self.screen_width, height=self.screen_height - 1)
            
        if self.colors_enabled:
            self.renderer.colors_enabled = True
        
        # Create player
        if self.is_multiplayer and self.client.local_player:
            # Use player from network client
            self.player = self.client.local_player
        else:
            # Create local player for solo mode
            spawn_x, spawn_y = self.game_map.get_spawn_point(0)
            self.player = Player(spawn_x, spawn_y, angle=0.0, player_id=0)
        
        # Create weapon manager and HUD
        self.weapon_manager = WeaponManager()
        self.weapon = WEAPON_RIFLE
        self.hud = HUD(self.screen_width, self.screen_height)
        
        # Other players (for multiplayer)
        self.other_players: List[Player] = []
        
        # Mouse tracking
        self.last_mouse_x = self.screen_width // 2
        self.mouse_sensitivity = sensitivity  # Radians per pixel
        
        # Input system
        self.use_evdev = False
        self.evdev_controller = None
        
        if use_evdev:
            try:
                # Enable debug mode with EVDEV_DEBUG environment variable
                import os
                debug_mode = os.environ.get('EVDEV_DEBUG', '0') == '1'
                controller = EvdevController(debug=debug_mode)
                if controller.error:
                     with open("kitty_debug.log", "a") as f:
                        f.write(f"Evdev init error: {controller.error}\n")
                elif controller.start():
                    self.evdev_controller = controller
                    self.use_evdev = True
                    with open("kitty_debug.log", "a") as f:
                        f.write(f"Evdev started on {controller.device.name}\n")
            except Exception as e:
                with open("kitty_debug.log", "a") as f:
                    import traceback
                    f.write(f"Evdev exception: {e}\n")
                    traceback.print_exc(file=f)

        self.use_pynput = False
        self.key_listener = None
        global PYNPUT_AVAILABLE
        
        if native_input and PYNPUT_AVAILABLE and not self.use_evdev:
            try:
                self.key_listener = keyboard.Listener(
                    on_press=self.on_pynput_press,
                    on_release=self.on_pynput_release
                )
                self.key_listener.start()
                self.use_pynput = True
                with open("kitty_debug.log", "a") as f:
                    f.write("Pynput listener started successfully\n")
            except Exception as e:
                # Fallback to curses if pynput fails (e.g. permission error)
                with open("kitty_debug.log", "a") as f:
                    f.write(f"Pynput failed to start: {e}\n")
                self.use_pynput = False
        
        # Key state tracking (for held keys)
        self.key_states = {
            'w': False, 's': False, 'a': False, 'd': False,
            'left': False, 'right': False
        }
        self.key_timestamps = {
            'w': 0.0, 's': 0.0, 'a': 0.0, 'd': 0.0,
            'left': 0.0, 'right': 0.0
        }
        self.key_decay = 0.05  # Time in seconds before key is considered released
        self.key_timers = {}  # For key repeat simulation
        
        # Timing
        self.last_time = time.time()
        self.fps = 0
        self.frame_count = 0
        self.fps_update_time = time.time()
    
    def on_pynput_press(self, key):
        """Callback for pynput key press."""
        try:
            # Debug log to see if we get anything
            with open("pynput_debug.log", "a") as f:
                f.write(f"Press: {key}\n")

            # Handle standard character keys
            if hasattr(key, 'char') and key.char:
                k = key.char.lower()
                if k in self.key_states:
                    self.key_states[k] = True
            
            # Handle special keys
            elif key == keyboard.Key.left:
                self.key_states['left'] = True
            elif key == keyboard.Key.right:
                self.key_states['right'] = True
                
        except AttributeError:
            # This can happen if key doesn't have char attribute and isn't a special key we check
            pass
        except Exception as e:
            # Log any other unexpected error
            with open("pynput_error.log", "a") as f:
                f.write(f"Press Error: {e}, Key: {key}\n")

    def on_pynput_release(self, key):
        """Callback for pynput key release."""
        try:
            if hasattr(key, 'char') and key.char:
                k = key.char.lower()
                if k in self.key_states:
                    self.key_states[k] = False
            elif key == keyboard.Key.left:
                self.key_states['left'] = False
            elif key == keyboard.Key.right:
                self.key_states['right'] = False
        except AttributeError:
            pass
        except Exception as e:
            with open("pynput_error.log", "a") as f:
                f.write(f"Release Error: {e}, Key: {key}\n")

    def handle_input(self, delta_time: float) -> None:
        """
        Handle keyboard and mouse input.
        """
        current_time = time.time()
        
        # Sync evdev state if active
        if self.use_evdev and self.evdev_controller:
            import os
            debug = os.environ.get('EVDEV_DEBUG', '0') == '1'
            
            for k in self.key_states:
                old_val = self.key_states[k]
                new_val = self.evdev_controller.get_key_state(k)
                self.key_states[k] = new_val
                
                if debug and old_val != new_val:
                    try:
                        with open("/tmp/evdev_game_sync.log", "a") as f:
                            f.write(f"[{current_time:.2f}] {k}: {old_val} -> {new_val}\n")
                    except:
                        pass
        
        # If using pynput, key_states are updated asynchronously
        # But we still need to process mouse and special keys via curses (like Quit or One-shot)
        
        # Process all input events from stdin (curses)
        while True:
            key = self.stdscr.getch()
            if key == -1:
                break
            
            # DEBUG: Log key
            # with open("input_debug.log", "a") as f:
            #     f.write(f"Key: {key}\n")
            
            # Use pynput for movement, so ignore movement keys from curses if pynput is active
            # UNLESS pynput failed.
            
            # Handle mouse events (Always use curses for mouse as pynput mouse grabs global cursor which is bad for terminal)
            if key == curses.KEY_MOUSE:
                try:
                    _, mx, my, _, bstate = curses.getmouse()
                    
                    # Mouse movement for rotation
                    dx = mx - self.last_mouse_x
                    if dx != 0:
                        self.player.angle += dx * self.mouse_sensitivity
                        # Normalize angle to [0, 2π]
                        self.player.angle = self.player.angle % (2 * math.pi)
                    self.last_mouse_x = mx
                    
                    # Left click to shoot
                    if bstate & curses.BUTTON1_PRESSED or bstate & curses.BUTTON1_CLICKED:
                        if self.player.try_shoot():
                            self.weapon_manager.shoot(
                                self.weapon, 
                                self.player.x, self.player.y, self.player.angle,
                                self.player.player_id
                            )
                            self.hud.add_message("BANG!", current_time)
                            if self.is_multiplayer and self.client:
                                self.client.send_shoot(self.player.x, self.player.y, self.player.angle)
                except curses.error:
                    pass
                continue
            
            # Quit
            if key == ord('q') or key == ord('Q'):
                # Disable mouse tracking before quitting
                print('\033[?1003l', end='', flush=True)
                # Disable keyboard protocol
                if self.graphics_mode == 'kitty':
                    sys.stdout.write('\033[<u')
                self.running = False
                return
            
            # Escape (Check for Kitty Protocol sequence)
            if key == 27:
                # Check if it's a sequence
                self.stdscr.nodelay(True)
                next_key = self.stdscr.getch()
                if next_key == ord('['):
                    # It's an escape sequence! Read until 'u' or timeout
                    seq = ""
                    start_read = time.time()
                    while True:
                        if time.time() - start_read > 0.01: break # Short timeout for parsing
                        k = self.stdscr.getch()
                        if k == -1: continue # Busy wait? No, standard getch might return -1 immediately
                        c = chr(k)
                        seq += c
                        if c == 'u' or not (c.isdigit() or c in ';:?<=>'): 
                            break
                    
                    if seq.endswith('u'):
                        # Parse Kitty Key Event
                        # Format: CSI code [; modifiers] [: event_type] u
                        try:
                            # Split by ':' to get event type
                            if ':' in seq:
                                parts = seq[:-1].split(':')
                                event_type_part = parts[1]
                                # Check if event type part has more info or just number
                                if ';' in event_type_part:
                                    event_type = int(event_type_part.split(';')[0])
                                else:
                                    event_type = int(event_type_part)
                                
                                code_part = parts[0]
                            else:
                                # Implicit event type 1 (press)? Or check docs
                                event_type = 1
                                code_part = seq[:-1]
                            
                            # Parse code part "<code>[;<modifiers>]"
                            if ';' in code_part:
                                code = int(code_part.split(';')[0])
                            else:
                                if code_part.startswith('='): code_part = code_part[1:] # Strip leading = if present
                                if code_part.startswith('>'): code_part = code_part[1:]
                                if code_part:
                                    code = int(code_part)
                                else:
                                    code = 0

                            # Map codes
                            key_name = None
                            if code == 119 or code == 87: key_name = 'w'
                            elif code == 115 or code == 83: key_name = 's'
                            elif code == 97 or code == 65: key_name = 'a'
                            elif code == 100 or code == 68: key_name = 'd'
                            elif code == 57419: key_name = 'left' # Keypad Left
                            elif code == 57421: key_name = 'right' # Keypad Right
                            
                            if key_name:
                                if event_type == 1 or event_type == 2: # Press or Repeat
                                    self.key_timestamps[key_name] = current_time + 1000.0 # Future timestamp = held
                                    self.key_states[key_name] = True
                                elif event_type == 3: # Release
                                    self.key_timestamps[key_name] = 0.0 # Released
                                    self.key_states[key_name] = False
                                    
                        except ValueError:
                            pass
                    continue
                else:
                    # Just ESC key (Quit)
                    if next_key == -1:
                        print('\033[?1003l', end='', flush=True)
                        if self.graphics_mode == 'kitty': 
                            sys.stdout.write('\033[<u')
                            sys.stdout.write('\033[=0u') # Reset flags
                        self.running = False
                        return
            
            # Update key timestamps (Standard Mode fallback)
            # Skip this entirely if using evdev or pynput - they handle it
            if not self.use_evdev and not self.use_pynput:
                # Even in Kitty mode, if the parser failed to catch an escape sequence (or terminal didn't send one),
                # we should still accept the basic character input.
                # The conflict is: Kitty sends press/release. Standard sends repeats.
                # If we mix them, standard repeats might re-trigger a key we just released?
                # BUT: if we are not moving at all, it means we are getting NOTHING.
                # So let's enable fallback but with a check.
                
                is_movement_key = False
                if key == ord('w') or key == ord('W'):
                    self.key_timestamps['w'] = current_time
                    is_movement_key = True
                if key == ord('s') or key == ord('S'):
                    self.key_timestamps['s'] = current_time
                    is_movement_key = True
                if key == ord('a') or key == ord('A'):
                    self.key_timestamps['a'] = current_time
                    is_movement_key = True
                if key == ord('d') or key == ord('D'):
                    self.key_timestamps['d'] = current_time
                    is_movement_key = True
                if key == curses.KEY_LEFT:
                    self.key_timestamps['left'] = current_time
                    is_movement_key = True
                if key == curses.KEY_RIGHT:
                    self.key_timestamps['right'] = current_time
                    is_movement_key = True
                
                # If we detected a movement key via standard input, ensure it's marked active
                # This ensures that even if Kitty protocol fails, we can move (albeit with decay logic)
                if is_movement_key and self.graphics_mode == 'kitty':
                     # We don't want to override explicit release events from kitty protocol
                     # But if we get a standard key press, it means the key IS down.
                     pass
            
            # One-shot actions
            if key == ord(' ') or key == 10:
                if self.player.try_shoot():
                    self.weapon_manager.shoot(
                        self.weapon, 
                        self.player.x, self.player.y, self.player.angle,
                        self.player.player_id
                    )
                    self.hud.add_message("BANG!", current_time)
                    if self.is_multiplayer and self.client:
                        self.client.send_shoot(self.player.x, self.player.y, self.player.angle)
            
            if key == ord('r') or key == ord('R'):
                self.player.reload()
            
            # Mouse sensitivity controls
            if key == ord(']') or key == ord('+'):
                self.mouse_sensitivity = min(1.0, self.mouse_sensitivity + 0.05)
                self.hud.add_message(f"Sensitivity: {self.mouse_sensitivity:.2f}", current_time)
            
            if key == ord('[') or key == ord('-'):
                self.mouse_sensitivity = max(0.01, self.mouse_sensitivity - 0.05)
                self.hud.add_message(f"Sensitivity: {self.mouse_sensitivity:.2f}", current_time)

        # Update key states based on decay
        # Even in Kitty mode, if we are getting standard keys (because protocol failed or mixed input),
        # we should respect the decay to ensure movement happens.
        # But for Kitty events (future timestamps), this check will return True (current < future)
        # So it is safe to run this for all modes EXCEPT pynput and evdev
        if not self.use_pynput and not self.use_evdev:
            for k, t in self.key_timestamps.items():
                self.key_states[k] = (current_time - t < self.key_decay) or (t > current_time)
        
        # Apply held movement keys
        import os
        debug = os.environ.get('EVDEV_DEBUG', '0') == '1'
        
        if debug:
            active = [k for k, v in self.key_states.items() if v]
            if active:
                try:
                    with open("/tmp/evdev_game_sync.log", "a") as f:
                        f.write(f"[{current_time:.2f}] Active keys: {active}\n")
                except:
                    pass
        
        if self.key_states['w']:
            self.player.move_forward(self.game_map, delta_time)
        if self.key_states['s']:
            self.player.move_backward(self.game_map, delta_time)
        if self.key_states['a']:
            self.player.strafe_left(self.game_map, delta_time)
        if self.key_states['d']:
            self.player.strafe_right(self.game_map, delta_time)
        if self.key_states['left']:
            self.player.rotate_left(delta_time)
        if self.key_states['right']:
            self.player.rotate_right(delta_time)
    
    def update(self, delta_time: float) -> None:
        """
        Update game state.
        
        Args:
            delta_time: Time since last frame in seconds
        """
        # Update multiplayer client
        if self.is_multiplayer and self.client:
            self.client.update(delta_time)
            # Get other players from client
            self.other_players = list(self.client.other_players.values())
        
        # Update player
        self.player.update(delta_time)
        
        # Update weapons and projectiles
        self.weapon_manager.update(delta_time, self.game_map)
        
        # Check projectile hits (in single player, no other targets yet)
        # In multiplayer, server handles authoritative hit detection
        
        # Update FPS counter
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.fps_update_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.fps_update_time = current_time
    
    def render(self) -> None:
        """Render the game with colors."""
        if self.graphics_mode != 'kitty':
            self.stdscr.clear()
        else:
            # In kitty mode, DO NOT clear the screen as it causes flickering.
            # We only need to overwrite the text lines.
            # erase() or clear() both send clear screen sequences in many curses implementations.
            # We will rely on overwriting the text.
            # To be safe, we can clear only the top lines (HUD) by writing spaces?
            # Actually, let's just NOT call clear/erase.
            # But we need to ensure old text is removed if strings get shorter.
            pass
        
        # Kitty Graphics Mode
        if self.graphics_mode == 'kitty':
            # We defer rendering until after HUD and refresh
            # This ensures the image is drawn on top or behind the text 
            # without being cleared by curses refresh
            pass
        
        else:
            # ASCII Rendering
            # Render 3D view with other players
            frame = self.renderer.render(
                self.game_map, 
                self.player.x, 
                self.player.y, 
                self.player.angle,
                self.other_players
            )
            
            # Draw frame with colors
            for y in range(len(frame[0]) if frame else 0):
                for x in range(min(len(frame), self.screen_width)):
                    char, color = frame[x][y]
                    try:
                        if self.colors_enabled:
                            self.stdscr.addstr(y, x, char, curses.color_pair(color))
                        else:
                            self.stdscr.addstr(y, x, char)
                    except curses.error:
                        pass
        
        # HUD Elements (Common for both modes)
        # Draw crosshair with color
        crosshair = self.hud.render_crosshair(self.screen_width, self.screen_height - 1)
        for x, y, char in crosshair:
            try:
                if self.colors_enabled:
                    self.stdscr.addstr(y, x, char, curses.color_pair(COLOR_CROSSHAIR) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(y, x, char)
            except curses.error:
                pass
        
        # Draw compass (top center)
        compass_width = 40
        compass_str = self.hud.render_compass(self.player.angle, compass_width)
        compass_x = (self.screen_width - compass_width) // 2
        try:
            # Draw with a background or distinct color if possible
            if self.colors_enabled:
                self.stdscr.addstr(1, compass_x, compass_str, curses.color_pair(COLOR_HUD) | curses.A_BOLD)
            else:
                self.stdscr.addstr(1, compass_x, compass_str)
            # Add a pointer below/above it
            pointer_x = compass_x + compass_width // 2
            self.stdscr.addstr(2, pointer_x, "^", curses.color_pair(COLOR_HUD) | curses.A_BOLD)
        except curses.error:
            pass

        # Draw minimap (top-right corner)
        minimap = self.hud.render_minimap(
            self.game_map, 
            self.player.x, 
            self.player.y, 
            self.other_players,
            player_angle=self.player.angle
        )
        minimap_x = self.screen_width - len(minimap[0]) - 2
        for i, line in enumerate(minimap):
            try:
                # Basic coloring for minimap
                if self.colors_enabled:
                    # Draw char by char to color walls/players
                    for cx, char in enumerate(line):
                        color = COLOR_HUD
                        if char == '#': color = COLOR_WALL_DIM
                        elif char in ['>', 'v', '<', '^', '↗', '↘', '↙', '↖']: color = COLOR_PLAYER
                        elif char == 'P': color = COLOR_PLAYER
                        self.stdscr.addstr(i + 1, minimap_x + cx, char, curses.color_pair(color))
                else:
                    self.stdscr.addstr(i + 1, minimap_x, line)
            except curses.error:
                pass
        
        # Draw messages (top-left) with color
        messages = self.hud.get_active_messages(time.time())
        for i, msg in enumerate(messages):
            try:
                if self.colors_enabled:
                    self.stdscr.addstr(i + 1, 2, msg, curses.color_pair(COLOR_HUD) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(i + 1, 2, msg)
            except curses.error:
                pass
        
        # Draw projectiles as simple indicators
        for projectile in self.weapon_manager.get_active_projectiles():
            px = int(projectile.x - self.player.x) + 7
            py = int(projectile.y - self.player.y) + 7
            if 0 <= px < 15 and 0 <= py < 15:
                try:
                    self.stdscr.addstr(py + 1, minimap_x + px, '*')
                except curses.error:
                    pass
        
        # Status line at bottom with colored health
        mode_str = "MULTIPLAYER" if self.is_multiplayer else "SOLO"
        if self.use_evdev:
            input_mode = "EVDEV"
        elif self.use_pynput:
            input_mode = "PYNPUT"
        elif self.graphics_mode == 'kitty':
            input_mode = "KITTY"
        else:
            input_mode = "STD"
        players_str = f"Players:{1 + len(self.other_players)}" if self.is_multiplayer else f"Projectiles:{len(self.weapon_manager.projectiles)}"
        status = self.hud.render_status_line(self.player, self.fps, f"{mode_str} | {input_mode} | {players_str}")
        
        # Choose health color
        if self.player.health > 70:
            health_color = COLOR_HEALTH_HIGH
        elif self.player.health > 30:
            health_color = COLOR_HEALTH_MED
        else:
            health_color = COLOR_HEALTH_LOW
        
        try:
            if self.colors_enabled:
                self.stdscr.addstr(self.screen_height - 1, 0, status[:self.screen_width - 1], 
                                   curses.color_pair(health_color))
            else:
                self.stdscr.addstr(self.screen_height - 1, 0, status[:self.screen_width - 1])
        except curses.error:
            pass
        
        self.stdscr.refresh()
        
        # Kitty Graphics Mode - Render here to overlay/underlay
        if self.graphics_mode == 'kitty':
            try:
                # Render to image buffer
                img = self.renderer.render(
                    self.game_map, 
                    self.player.x, 
                    self.player.y, 
                    self.player.angle,
                    self.other_players
                )
                
                # Render command
                cmd = serialize_image_cmd(
                    img, 
                    z_index=-1,  # Behind text
                    quiet=2,
                    cols=self.screen_width, # Scale to terminal width
                    rows=self.screen_height, # Scale to terminal height
                    img_id=1 # Use fixed ID 1 for persistent background
                )
                
                # Move cursor to home (H) but do NOT clear screen (2J)
                sys.stdout.write("\033[H") 
                sys.stdout.write(cmd)
                sys.stdout.flush()
                
            except Exception as e:
                # Log error
                with open("kitty_debug.log", "a") as f:
                    import traceback
                    f.write(f"Render error: {e}\n")
                    traceback.print_exc(file=f)
    
    def run(self) -> None:
        """Main game loop."""
        try:
            while self.running:
                # Calculate delta time
                current_time = time.time()
                delta_time = current_time - self.last_time
                self.last_time = current_time
                
                # Limit frame rate
                if delta_time < 1.0 / 60:
                    time.sleep(1.0 / 60 - delta_time)
                    delta_time = 1.0 / 60
                
                # Game loop
                self.handle_input(delta_time)
                self.update(delta_time)
                self.render()
        finally:
            # Stop evdev controller
            if self.evdev_controller:
                self.evdev_controller.stop()
            
            # Stop pynput listener
            if self.key_listener:
                self.key_listener.stop()
            
            # Disable mouse tracking when game ends
            print('\033[?1003l', end='', flush=True)


def start_game(stdscr, game_map: Optional[Map] = None, client: Optional[GameClient] = None, sensitivity: float = 0.15, graphics_mode: str = 'ascii', native_input: bool = False, use_evdev: bool = False):
    """
    Entry point for starting the game with curses.
    
    Args:
        stdscr: Curses standard screen
        game_map: Optional game map
        client: Optional network client for multiplayer
        sensitivity: Mouse sensitivity (default 0.15)
        graphics_mode: Graphics mode ('ascii' or 'kitty')
        native_input: Whether to try using pynput
        use_evdev: Whether to use evdev
    """
    game = Game(stdscr, game_map, client, sensitivity, graphics_mode, native_input, use_evdev)
    game.run()
    
    # Disconnect client if multiplayer
    if client:
        client.disconnect()


if __name__ == "__main__":
    # Test mode: run the game
    try:
        curses.wrapper(start_game)
    except KeyboardInterrupt:
        print("\nGame interrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
