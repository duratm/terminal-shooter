"""
Game module - Main game loop and state management.
"""

import curses
import time
import math
from typing import Optional, List

from .map import Map, create_default_map
from .renderer import Renderer, init_colors, COLOR_CROSSHAIR, COLOR_HUD, COLOR_HEALTH_HIGH, COLOR_HEALTH_MED, COLOR_HEALTH_LOW, COLOR_PLAYER, COLOR_WALL_DIM
from .player import Player
from .weapons import WeaponManager, WEAPON_RIFLE
from .ui.hud import HUD
from .network.client import GameClient


class Game:
    """Main game class managing the game loop and state."""
    
    def __init__(self, stdscr, game_map: Optional[Map] = None, client: Optional[GameClient] = None):
        """
        Initialize the game.
        
        Args:
            stdscr: Curses standard screen object
            game_map: Game map (creates default if None)
            client: Network client for multiplayer (None for solo)
        """
        self.stdscr = stdscr
        self.running = True
        self.client = client  # Network client for multiplayer
        self.is_multiplayer = client is not None
        
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
        
        # Get screen dimensions
        self.screen_height, self.screen_width = stdscr.getmaxyx()
        
        # Create map and renderer
        self.game_map = game_map if game_map else create_default_map()
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
        self.mouse_sensitivity = 0.15  # Radians per pixel
        
        # Key state tracking (for held keys)
        self.key_states = {
            'w': False, 's': False, 'a': False, 'd': False,
            'left': False, 'right': False
        }
        self.key_timers = {}  # For key repeat simulation
        
        # Timing
        self.last_time = time.time()
        self.fps = 0
        self.frame_count = 0
        self.fps_update_time = time.time()
    
    def handle_input(self, delta_time: float) -> None:
        """
        Handle keyboard and mouse input.
        
        - Mouse movement rotates the camera
        - Left click shoots
        - WASD for movement
        - Arrow keys also rotate (keyboard fallback)
        
        Args:
            delta_time: Time since last frame in seconds
        """
        current_time = time.time()
        
        # Reset key states each frame - will be set if key is in buffer
        for k in self.key_states:
            self.key_states[k] = False
        
        # Process all input events
        while True:
            key = self.stdscr.getch()
            if key == -1:
                break
            
            # Handle mouse events
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
            if key == ord('q') or key == ord('Q') or key == 27:
                # Disable mouse tracking before quitting
                print('\033[?1003l', end='', flush=True)
                self.running = False
                return
            
            # Mark movement keys as held
            if key == ord('w') or key == ord('W'):
                self.key_states['w'] = True
            if key == ord('s') or key == ord('S'):
                self.key_states['s'] = True
            if key == ord('a') or key == ord('A'):
                self.key_states['a'] = True
            if key == ord('d') or key == ord('D'):
                self.key_states['d'] = True
            if key == curses.KEY_LEFT:
                self.key_states['left'] = True
            if key == curses.KEY_RIGHT:
                self.key_states['right'] = True
            
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
        
        # Apply held movement keys
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
        self.stdscr.clear()
        
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
        players_str = f"Players:{1 + len(self.other_players)}" if self.is_multiplayer else f"Projectiles:{len(self.weapon_manager.projectiles)}"
        status = self.hud.render_status_line(self.player, self.fps, f"{mode_str} | {players_str}")
        
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
            # Disable mouse tracking when game ends
            print('\033[?1003l', end='', flush=True)


def start_game(stdscr, game_map: Optional[Map] = None, client: Optional[GameClient] = None):
    """
    Entry point for starting the game with curses.
    
    Args:
        stdscr: Curses standard screen
        game_map: Optional game map
        client: Optional network client for multiplayer
    """
    game = Game(stdscr, game_map, client)
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
