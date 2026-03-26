"""
Game module - Main game loop and state management.
"""

import curses
import time
import math
from typing import Optional, List

from .map import Map, create_default_map
from .renderer import Renderer
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
        
        # Get screen dimensions
        self.screen_height, self.screen_width = stdscr.getmaxyx()
        
        # Create map and renderer
        self.game_map = game_map if game_map else create_default_map()
        self.renderer = Renderer(width=self.screen_width, height=self.screen_height - 1)
        
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
        
        # Timing
        self.last_time = time.time()
        self.fps = 0
        self.frame_count = 0
        self.fps_update_time = time.time()
    
    def handle_input(self, delta_time: float) -> None:
        """
        Handle keyboard input.
        
        Args:
            delta_time: Time since last frame in seconds
        """
        key = self.stdscr.getch()
        
        if key == -1:  # No input
            return
        
        # Movement (WASD)
        if key == ord('w') or key == ord('W'):
            self.player.move_forward(self.game_map, delta_time)
        
        elif key == ord('s') or key == ord('S'):
            self.player.move_backward(self.game_map, delta_time)
        
        elif key == ord('a') or key == ord('A'):
            self.player.strafe_left(self.game_map, delta_time)
        
        elif key == ord('d') or key == ord('D'):
            self.player.strafe_right(self.game_map, delta_time)
        
        # Rotation (Arrow keys)
        elif key == curses.KEY_LEFT:
            self.player.rotate_left(delta_time)
        
        elif key == curses.KEY_RIGHT:
            self.player.rotate_right(delta_time)
        
        # Shooting
        elif key == ord(' ') or key == 10:  # Space or Enter
            if self.player.try_shoot():
                # Create projectile locally
                projectile = self.weapon_manager.shoot(
                    self.weapon, 
                    self.player.x, 
                    self.player.y, 
                    self.player.angle,
                    self.player.player_id
                )
                self.hud.add_message("BANG!", time.time())
                
                # Send shoot message to server if multiplayer
                if self.is_multiplayer and self.client:
                    self.client.send_shoot(self.player.x, self.player.y, self.player.angle)
        
        # Reload
        elif key == ord('r') or key == ord('R'):
            self.player.reload()
        
        # Quit
        elif key == ord('q') or key == ord('Q') or key == 27:  # ESC
            self.running = False
    
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
        """Render the game."""
        self.stdscr.clear()
        
        # Render 3D view with other players
        frame = self.renderer.render(
            self.game_map, 
            self.player.x, 
            self.player.y, 
            self.player.angle,
            self.other_players  # Pass other players for rendering
        )
        
        for y, row in enumerate(frame):
            try:
                self.stdscr.addstr(y, 0, row)
            except curses.error:
                pass  # Ignore errors when writing to last position
        
        # Draw crosshair
        crosshair = self.hud.render_crosshair(self.screen_width, self.screen_height - 1)
        for x, y, char in crosshair:
            try:
                self.stdscr.addstr(y, x, char)
            except curses.error:
                pass
        
        # Draw minimap (top-right corner)
        minimap = self.hud.render_minimap(self.game_map, self.player.x, self.player.y, self.other_players)
        minimap_x = self.screen_width - len(minimap[0]) - 2
        for i, line in enumerate(minimap):
            try:
                self.stdscr.addstr(i + 1, minimap_x, line)
            except curses.error:
                pass
        
        # Draw messages (top-left)
        messages = self.hud.get_active_messages(time.time())
        for i, msg in enumerate(messages):
            try:
                self.stdscr.addstr(i + 1, 2, msg)
            except curses.error:
                pass
        
        # Draw projectiles as simple indicators
        for projectile in self.weapon_manager.get_active_projectiles():
            # Simple 2D representation on minimap
            px = int(projectile.x - self.player.x) + minimap.size // 2 if hasattr(minimap, 'size') else 7
            py = int(projectile.y - self.player.y) + minimap.size // 2 if hasattr(minimap, 'size') else 7
            if 0 <= px < 15 and 0 <= py < 15:
                try:
                    self.stdscr.addstr(py + 1, minimap_x + px, '*')
                except curses.error:
                    pass
        
        # Status line at bottom
        mode_str = "MULTIPLAYER" if self.is_multiplayer else "SOLO"
        players_str = f"Players:{1 + len(self.other_players)}" if self.is_multiplayer else f"Projectiles:{len(self.weapon_manager.projectiles)}"
        status = self.hud.render_status_line(self.player, self.fps, f"{mode_str} | {players_str}")
        try:
            self.stdscr.addstr(self.screen_height - 1, 0, status[:self.screen_width - 1])
        except curses.error:
            pass
        
        self.stdscr.refresh()
    
    def run(self) -> None:
        """Main game loop."""
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
