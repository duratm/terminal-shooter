"""
Client module for Terminal Shooter.
Handles client-side networking for multiplayer.
"""

import socket
import threading
import time
import queue
from typing import Optional, Dict

from .protocol import (
    NetworkMessage, MessageType,
    create_connect_message, create_position_update,
    create_shoot_message, create_ping_message
)
from ..player import Player


class GameClient:
    """Multiplayer game client."""
    
    def __init__(self, server_host: str, server_port: int = 5555, player_name: str = "Player"):
        """
        Initialize game client.
        
        Args:
            server_host: Server IP address
            server_port: Server port
            player_name: Player display name
        """
        self.server_host = server_host
        self.server_port = server_port
        self.player_name = player_name
        
        # Network
        self.tcp_socket: Optional[socket.socket] = None
        self.udp_socket: Optional[socket.socket] = None
        self.connected = False
        
        # Player state
        self.player_id: Optional[int] = None
        self.local_player: Optional[Player] = None
        self.other_players: Dict[int, Player] = {}
        
        # Message queues
        self.incoming_messages = queue.Queue()
        
        # Threads
        self.udp_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Timing
        self.last_update_time = 0.0
        self.update_rate = 20  # Updates per second
    
    def connect(self) -> bool:
        """
        Connect to the game server.
        
        Returns:
            True if connected successfully
        """
        try:
            # Create TCP connection
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.settimeout(5.0)
            self.tcp_socket.connect((self.server_host, self.server_port))
            
            # Send connect message
            connect_msg = create_connect_message(0, self.player_name)
            self.tcp_socket.send(connect_msg.to_bytes())
            
            # Receive acknowledgment
            data = self.tcp_socket.recv(1024)
            ack_msg = NetworkMessage.from_bytes(data)
            
            if not ack_msg or ack_msg.msg_type != MessageType.CONNECT_ACK:
                print("❌ Server rejected connection")
                return False
            
            # Extract player ID and spawn info
            self.player_id = ack_msg.data.get('assigned_id')
            game_state = ack_msg.data.get('game_state', {})
            spawn_x = game_state.get('spawn_x', 5.0)
            spawn_y = game_state.get('spawn_y', 5.0)
            
            # Create local player
            self.local_player = Player(spawn_x, spawn_y, 0.0, self.player_id)
            
            # Create UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.settimeout(0.1)
            
            # Start UDP receive thread
            self.running = True
            self.udp_thread = threading.Thread(target=self._udp_receive_loop, daemon=True)
            self.udp_thread.start()
            
            self.connected = True
            print(f"✅ Connected to server as Player {self.player_id}")
            print(f"   Spawn: ({spawn_x:.1f}, {spawn_y:.1f})")
            print(f"   Players online: {game_state.get('player_count', 1)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            self.disconnect()
            return False
    
    def disconnect(self) -> None:
        """Disconnect from server."""
        print("\n🔌 Disconnecting...")
        self.running = False
        self.connected = False
        
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
        
        print("✅ Disconnected")
    
    def _udp_receive_loop(self) -> None:
        """Receive UDP messages from server."""
        while self.running:
            try:
                data, _ = self.udp_socket.recvfrom(1024)
                msg = NetworkMessage.from_bytes(data)
                
                if msg:
                    self.incoming_messages.put(msg)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    pass  # Ignore errors
    
    def send_position_update(self, x: float, y: float, angle: float) -> None:
        """Send position update to server."""
        if not self.connected or not self.udp_socket:
            return
        
        msg = create_position_update(self.player_id, x, y, angle)
        try:
            self.udp_socket.sendto(msg.to_bytes(), (self.server_host, self.server_port))
        except:
            pass
    
    def send_shoot(self, x: float, y: float, angle: float) -> None:
        """Send shoot message to server."""
        if not self.connected or not self.udp_socket:
            return
        
        msg = create_shoot_message(self.player_id, x, y, angle)
        try:
            self.udp_socket.sendto(msg.to_bytes(), (self.server_host, self.server_port))
        except:
            pass
    
    def process_messages(self) -> list:
        """
        Process incoming messages from server.
        
        Returns:
            List of processed messages
        """
        messages = []
        
        while not self.incoming_messages.empty():
            try:
                msg = self.incoming_messages.get_nowait()
                messages.append(msg)
                
                # Handle message
                if msg.msg_type == MessageType.POSITION_UPDATE:
                    player_id = msg.data.get('player_id')
                    
                    # Don't update local player from server (client-side prediction)
                    if player_id == self.player_id:
                        continue
                    
                    # Update or create other player
                    if player_id not in self.other_players:
                        self.other_players[player_id] = Player(
                            msg.data.get('x', 0),
                            msg.data.get('y', 0),
                            msg.data.get('angle', 0),
                            player_id
                        )
                    else:
                        player = self.other_players[player_id]
                        player.x = msg.data.get('x', player.x)
                        player.y = msg.data.get('y', player.y)
                        player.angle = msg.data.get('angle', player.angle)
                
                elif msg.msg_type == MessageType.SHOOT:
                    # Another player shot
                    pass  # Handled by game
                
                elif msg.msg_type == MessageType.HIT:
                    # Someone was hit
                    target_id = msg.data.get('target_id')
                    damage = msg.data.get('damage', 0)
                    
                    if target_id == self.player_id and self.local_player:
                        self.local_player.take_damage(damage)
                
                elif msg.msg_type == MessageType.PLAYER_DIED:
                    player_id = msg.data.get('player_id')
                    if player_id in self.other_players:
                        self.other_players[player_id].is_alive = False
                
                elif msg.msg_type == MessageType.PLAYER_RESPAWN:
                    player_id = msg.data.get('player_id')
                    x = msg.data.get('x', 5.0)
                    y = msg.data.get('y', 5.0)
                    angle = msg.data.get('angle', 0.0)
                    
                    if player_id == self.player_id and self.local_player:
                        self.local_player.respawn(x, y, angle)
                    elif player_id in self.other_players:
                        self.other_players[player_id].respawn(x, y, angle)
                    
            except queue.Empty:
                break
        
        return messages
    
    def update(self, delta_time: float) -> None:
        """
        Update client state.
        
        Args:
            delta_time: Time since last update
        """
        # Process incoming messages
        self.process_messages()
        
        # Send periodic updates
        current_time = time.time()
        if current_time - self.last_update_time >= 1.0 / self.update_rate:
            if self.local_player:
                self.send_position_update(
                    self.local_player.x,
                    self.local_player.y,
                    self.local_player.angle
                )
            self.last_update_time = current_time


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.network.client <server_ip>")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    
    print("=" * 60)
    print("    TERMINAL SHOOTER - CLIENT")
    print("=" * 60)
    
    client = GameClient(server_ip, player_name="TestPlayer")
    
    if client.connect():
        print("\n✅ Connection successful!")
        print("Press Ctrl+C to disconnect...")
        
        try:
            while client.connected:
                time.sleep(0.1)
                client.update(0.1)
        except KeyboardInterrupt:
            print()
    
    client.disconnect()
