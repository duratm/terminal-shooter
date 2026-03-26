"""
Server module for Terminal Shooter.
Handles multiplayer game server with authoritative state.
"""

import socket
import threading
import time
import select
from typing import Dict, List, Optional
from dataclasses import dataclass

from .protocol import (
    NetworkMessage, MessageType,
    create_connect_ack_message, create_position_update,
    create_shoot_message, create_hit_message,
    create_player_died_message, create_player_respawn_message,
    create_score_update_message
)
from ..player import Player
from ..map import Map, create_default_map
from ..weapons import WeaponManager, WEAPON_RIFLE


@dataclass
class ClientConnection:
    """Represents a connected client."""
    player_id: int
    address: tuple
    tcp_socket: socket.socket
    last_seen: float
    player: Player


class GameServer:
    """Multiplayer game server."""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 5555, max_players: int = 8):
        """
        Initialize game server.
        
        Args:
            host: Host address to bind to
            port: Port number
            max_players: Maximum number of players
        """
        self.host = host
        self.port = port
        self.max_players = max_players
        
        # Network sockets
        self.tcp_socket: Optional[socket.socket] = None
        self.udp_socket: Optional[socket.socket] = None
        
        # Game state
        self.game_map = create_default_map()
        self.weapon_manager = WeaponManager()
        self.clients: Dict[int, ClientConnection] = {}
        self.next_player_id = 1
        
        # Server control
        self.running = False
        self.game_started = False
        
        # Threads
        self.tcp_thread: Optional[threading.Thread] = None
        self.udp_thread: Optional[threading.Thread] = None
        self.game_thread: Optional[threading.Thread] = None
        
        # Timing
        self.tick_rate = 30  # Server ticks per second
        self.last_tick = time.time()
    
    def start(self) -> bool:
        """
        Start the game server.
        
        Returns:
            True if started successfully
        """
        try:
            # Create TCP socket for connections
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind((self.host, self.port))
            self.tcp_socket.listen(self.max_players)
            self.tcp_socket.settimeout(1.0)
            
            # Create UDP socket for gameplay
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind((self.host, self.port))
            self.udp_socket.settimeout(0.1)
            
            self.running = True
            
            # Start threads
            self.tcp_thread = threading.Thread(target=self._tcp_accept_loop, daemon=True)
            self.udp_thread = threading.Thread(target=self._udp_receive_loop, daemon=True)
            self.game_thread = threading.Thread(target=self._game_loop, daemon=True)
            
            self.tcp_thread.start()
            self.udp_thread.start()
            self.game_thread.start()
            
            print(f"✅ Server started on {self.host}:{self.port}")
            print(f"   Waiting for players (max: {self.max_players})...")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            self.stop()
            return False
    
    def stop(self) -> None:
        """Stop the game server."""
        print("\n🛑 Stopping server...")
        self.running = False
        
        # Close all client connections
        for client in list(self.clients.values()):
            try:
                client.tcp_socket.close()
            except:
                pass
        
        # Close server sockets
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
        
        print("✅ Server stopped")
    
    def _tcp_accept_loop(self) -> None:
        """Accept new TCP connections."""
        while self.running:
            try:
                client_socket, address = self.tcp_socket.accept()
                self._handle_new_connection(client_socket, address)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️  TCP accept error: {e}")
    
    def _handle_new_connection(self, client_socket: socket.socket, address: tuple) -> None:
        """Handle a new client connection."""
        try:
            # Receive connect message
            data = client_socket.recv(1024)
            msg = NetworkMessage.from_bytes(data)
            
            if msg and msg.msg_type == MessageType.CONNECT:
                # Check if server is full
                if len(self.clients) >= self.max_players:
                    print(f"❌ Connection from {address} rejected: Server full")
                    client_socket.close()
                    return
                
                # Assign player ID
                player_id = self.next_player_id
                self.next_player_id += 1
                
                # Create player
                spawn_point = len(self.clients) % len(self.game_map.spawn_points)
                spawn_x, spawn_y = self.game_map.get_spawn_point(spawn_point)
                player = Player(spawn_x, spawn_y, 0.0, player_id)
                
                # Store client
                client = ClientConnection(
                    player_id=player_id,
                    address=address,
                    tcp_socket=client_socket,
                    last_seen=time.time(),
                    player=player
                )
                self.clients[player_id] = client
                
                # Send acknowledgment
                game_state = {
                    'map_size': (self.game_map.width, self.game_map.height),
                    'spawn_x': spawn_x,
                    'spawn_y': spawn_y,
                    'player_count': len(self.clients)
                }
                ack_msg = create_connect_ack_message(
                    msg.data.get('player_id', 0),
                    player_id,
                    game_state
                )
                client_socket.send(ack_msg.to_bytes())
                
                player_name = msg.data.get('player_name', f'Player{player_id}')
                print(f"✅ {player_name} connected (ID: {player_id}) from {address}")
                print(f"   Players online: {len(self.clients)}/{self.max_players}")
                
                # Start game if we have players
                if not self.game_started and len(self.clients) >= 1:
                    self.game_started = True
                    print("\n🎮 Game started!")
                
        except Exception as e:
            print(f"⚠️  Error handling connection: {e}")
            client_socket.close()
    
    def _udp_receive_loop(self) -> None:
        """Receive and process UDP messages."""
        while self.running:
            try:
                data, address = self.udp_socket.recvfrom(1024)
                msg = NetworkMessage.from_bytes(data)
                
                if msg:
                    self._handle_udp_message(msg, address)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    pass  # Ignore UDP errors
    
    def _handle_udp_message(self, msg: NetworkMessage, address: tuple) -> None:
        """Handle a UDP message from a client."""
        player_id = msg.data.get('player_id')
        
        if player_id not in self.clients:
            return
        
        client = self.clients[player_id]
        client.last_seen = time.time()
        
        # Handle different message types
        if msg.msg_type == MessageType.POSITION_UPDATE:
            # Update player position
            client.player.x = msg.data.get('x', client.player.x)
            client.player.y = msg.data.get('y', client.player.y)
            client.player.angle = msg.data.get('angle', client.player.angle)
            
        elif msg.msg_type == MessageType.SHOOT:
            # Handle shooting
            if client.player.is_alive:
                projectile = self.weapon_manager.shoot(
                    WEAPON_RIFLE,
                    msg.data.get('x', client.player.x),
                    msg.data.get('y', client.player.y),
                    msg.data.get('angle', client.player.angle),
                    player_id
                )
                # Broadcast shoot event to all clients
                self._broadcast_udp(msg)
    
    def _game_loop(self) -> None:
        """Main game loop running on the server."""
        while self.running:
            current_time = time.time()
            delta_time = current_time - self.last_tick
            
            if delta_time < 1.0 / self.tick_rate:
                time.sleep(0.001)
                continue
            
            self.last_tick = current_time
            
            if not self.game_started:
                continue
            
            # Update game state
            self._update_game(delta_time)
            
            # Send state updates to clients
            self._send_state_updates()
            
            # Check for disconnected clients
            self._check_timeouts()
    
    def _update_game(self, delta_time: float) -> None:
        """Update game state."""
        # Update all players
        for client in self.clients.values():
            client.player.update(delta_time)
        
        # Update weapons/projectiles
        self.weapon_manager.update(delta_time, self.game_map)
        
        # Check for hits
        for client in self.clients.values():
            if not client.player.is_alive:
                continue
            
            hits = self.weapon_manager.check_hits(
                client.player.x,
                client.player.y,
                client.player.player_id
            )
            
            for projectile in hits:
                # Apply damage
                died = client.player.take_damage(projectile.damage)
                
                # Send hit message
                hit_msg = create_hit_message(
                    projectile.shooter_id,
                    client.player.player_id,
                    projectile.damage
                )
                self._broadcast_udp(hit_msg)
                
                # Handle death
                if died:
                    # Update killer's score
                    if projectile.shooter_id in self.clients:
                        shooter = self.clients[projectile.shooter_id]
                        shooter.player.kills += 1
                    
                    # Send death message
                    death_msg = create_player_died_message(
                        client.player.player_id,
                        projectile.shooter_id
                    )
                    self._broadcast_udp(death_msg)
                    
                    # Respawn after delay
                    threading.Timer(3.0, self._respawn_player, args=(client.player.player_id,)).start()
    
    def _respawn_player(self, player_id: int) -> None:
        """Respawn a player."""
        if player_id not in self.clients:
            return
        
        client = self.clients[player_id]
        spawn_point = player_id % len(self.game_map.spawn_points)
        spawn_x, spawn_y = self.game_map.get_spawn_point(spawn_point)
        
        client.player.respawn(spawn_x, spawn_y)
        
        # Send respawn message
        respawn_msg = create_player_respawn_message(player_id, spawn_x, spawn_y, 0.0)
        self._broadcast_udp(respawn_msg)
    
    def _send_state_updates(self) -> None:
        """Send periodic state updates to all clients."""
        # Send position updates for all players
        for client in self.clients.values():
            pos_msg = create_position_update(
                client.player.player_id,
                client.player.x,
                client.player.y,
                client.player.angle
            )
            self._broadcast_udp(pos_msg)
    
    def _broadcast_udp(self, msg: NetworkMessage) -> None:
        """Broadcast a UDP message to all clients."""
        data = msg.to_bytes()
        for client in self.clients.values():
            try:
                self.udp_socket.sendto(data, client.address)
            except:
                pass
    
    def _check_timeouts(self) -> None:
        """Check for disconnected clients."""
        current_time = time.time()
        timeout = 10.0  # seconds
        
        disconnected = []
        for player_id, client in self.clients.items():
            if current_time - client.last_seen > timeout:
                disconnected.append(player_id)
        
        for player_id in disconnected:
            client = self.clients[player_id]
            print(f"⚠️  Player {player_id} timed out")
            try:
                client.tcp_socket.close()
            except:
                pass
            del self.clients[player_id]


def run_server(host: str = '0.0.0.0', port: int = 5555):
    """Run the game server."""
    server = GameServer(host, port)
    
    if not server.start():
        return 1
    
    try:
        print("\n📋 Server Commands:")
        print("  'quit' or 'q'  - Stop server")
        print("  'status'       - Show server status")
        print("  'players'      - List connected players")
        
        while server.running:
            try:
                cmd = input("> ").strip().lower()
                
                if cmd in ('quit', 'q'):
                    break
                elif cmd == 'status':
                    print(f"\n📊 Server Status:")
                    print(f"   Players: {len(server.clients)}/{server.max_players}")
                    print(f"   Game Started: {server.game_started}")
                    print(f"   Tick Rate: {server.tick_rate} Hz")
                elif cmd == 'players':
                    print(f"\n👥 Connected Players:")
                    for client in server.clients.values():
                        print(f"   ID {client.player.player_id}: {client.address} - K:{client.player.kills} D:{client.player.deaths}")
                        
            except EOFError:
                break
            except KeyboardInterrupt:
                break
    
    finally:
        server.stop()
    
    return 0


if __name__ == "__main__":
    import sys
    run_server()
