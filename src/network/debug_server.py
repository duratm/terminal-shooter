"""
Debug version of the server with detailed event logging.
Use this to see all events the server receives.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.network.server import GameServer
from src.network.protocol import NetworkMessage, MessageType
import time

class DebugGameServer(GameServer):
    """Game server with debug logging enabled."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_count = 0
        self.last_broadcast_log = 0  # Track last broadcast log time
        print("\n" + "="*60)
        print("🔍 DEBUG SERVER MODE ENABLED")
        print("="*60)
        print("This will show all events received by the server.")
        print("Press Ctrl+C to stop.\n")
    
    def _handle_new_connection(self, client_socket, address):
        """Override with debug logging."""
        print(f"\n{'='*60}")
        print(f"🔌 NEW CONNECTION ATTEMPT from {address}")
        print(f"{'='*60}")
        
        try:
            # Receive connect message
            data = client_socket.recv(1024)
            msg = NetworkMessage.from_bytes(data)
            
            print(f"📩 Received message: {msg.msg_type if msg else 'INVALID'}")
            if msg and msg.data:
                print(f"📦 Message data: {msg.data}")
            
            if msg and msg.msg_type == MessageType.CONNECT:
                # Check if server is full
                if len(self.clients) >= self.max_players:
                    print(f"❌ REJECTED: Server full ({len(self.clients)}/{self.max_players})")
                    client_socket.close()
                    return
                
                # Assign player ID
                player_id = self.next_player_id
                self.next_player_id += 1
                
                # Create player
                from src.player import Player
                spawn_point = len(self.clients) % len(self.game_map.spawn_points)
                spawn_x, spawn_y = self.game_map.get_spawn_point(spawn_point)
                player = Player(spawn_x, spawn_y, 0.0, player_id)
                
                print(f"✅ ACCEPTED: Assigning ID {player_id}")
                print(f"   Spawn point: ({spawn_x:.1f}, {spawn_y:.1f})")
                print(f"   Total players: {len(self.clients) + 1}/{self.max_players}")
                
                # Store client
                from src.network.server import ClientConnection
                client = ClientConnection(
                    player_id=player_id,
                    address=address,
                    tcp_socket=client_socket,
                    last_seen=time.time(),
                    player=player
                )
                self.clients[player_id] = client
                
                # Send acknowledgment
                from src.network.protocol import create_connect_ack_message
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
            print(f"⚠️  ERROR handling connection: {e}")
            import traceback
            traceback.print_exc()
            client_socket.close()
    
    def _handle_udp_message(self, msg, address):
        """Override with debug logging."""
        self.event_count += 1
        player_id = msg.data.get('player_id', 'UNKNOWN')
        
        # Print event summary
        event_type = msg.msg_type.name if hasattr(msg.msg_type, 'name') else str(msg.msg_type)
        
        # Print every 10th event or important events
        if self.event_count % 10 == 0 or msg.msg_type == MessageType.SHOOT:
            print(f"\n📨 Event #{self.event_count}: {event_type} from Player {player_id}")
            
            if msg.msg_type == MessageType.POSITION_UPDATE:
                x = msg.data.get('x', 0)
                y = msg.data.get('y', 0)
                angle = msg.data.get('angle', 0)
                print(f"   Position: ({x:.2f}, {y:.2f}), Angle: {angle:.2f}")
                
            elif msg.msg_type == MessageType.SHOOT:
                print(f"   🔫 SHOT FIRED!")
                print(f"   Data: {msg.data}")
        
        # Call original handler
        super()._handle_udp_message(msg, address)
    
    def _send_state_updates(self):
        """Override to log state broadcasts."""
        if len(self.clients) == 0:
            return
            
        # Print periodic summary (every 5 seconds)
        current_time = time.time()
        if current_time - self.last_broadcast_log >= 5.0:
            self.last_broadcast_log = current_time
            print(f"\n📡 Broadcasting state to {len(self.clients)} clients")
            for client_id, client in self.clients.items():
                print(f"   Player {client_id}: ({client.player.x:.1f}, {client.player.y:.1f}) "
                      f"HP:{client.player.health} Alive:{client.player.is_alive}")
        
        # Call original method
        super()._send_state_updates()
    
    def _check_timeouts(self):
        """Override to log disconnections."""
        before_count = len(self.clients)
        super()._check_timeouts()
        after_count = len(self.clients)
        
        if before_count != after_count:
            print(f"\n⚠️  Player disconnected! {before_count} -> {after_count} players")


if __name__ == '__main__':
    print("\n" + "🎮 TERMINAL SHOOTER - DEBUG SERVER 🎮".center(60))
    print("="*60 + "\n")
    
    server = DebugGameServer(host='0.0.0.0', port=5555, max_players=8)
    
    if server.start():
        try:
            print("\n💡 TIP: Watch this terminal while players connect and play")
            print("💡 You'll see all network events in real-time\n")
            
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down...")
            server.stop()
    else:
        print("❌ Failed to start debug server")
        sys.exit(1)
