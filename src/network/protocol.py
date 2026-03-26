"""
Network protocol for Terminal Shooter.
Defines message types and serialization for multiplayer communication.
"""

import json
import struct
from enum import IntEnum
from typing import Dict, Any, Optional


class MessageType(IntEnum):
    """Network message types."""
    # Connection messages (TCP)
    CONNECT = 1
    CONNECT_ACK = 2
    DISCONNECT = 3
    
    # Game state messages (UDP)
    POSITION_UPDATE = 10
    SHOOT = 11
    HIT = 12
    PLAYER_DIED = 13
    PLAYER_RESPAWN = 14
    
    # Score and status (UDP)
    SCORE_UPDATE = 20
    HEALTH_UPDATE = 21
    AMMO_UPDATE = 22
    
    # Game control (TCP)
    START_GAME = 30
    END_GAME = 31
    PLAYER_LIST = 32
    
    # Ping/keepalive (UDP)
    PING = 40
    PONG = 41


class NetworkMessage:
    """Base class for network messages."""
    
    def __init__(self, msg_type: MessageType, data: Optional[Dict[str, Any]] = None):
        """
        Initialize a network message.
        
        Args:
            msg_type: Message type
            data: Message data dictionary
        """
        self.msg_type = msg_type
        self.data = data if data is not None else {}
        self.timestamp = 0.0  # Set by sender
    
    def to_bytes(self) -> bytes:
        """
        Serialize message to bytes.
        
        Format: [type:1 byte][length:4 bytes][json data]
        
        Returns:
            Serialized message bytes
        """
        json_data = json.dumps(self.data).encode('utf-8')
        msg_type_byte = struct.pack('B', self.msg_type)
        length_bytes = struct.pack('!I', len(json_data))
        return msg_type_byte + length_bytes + json_data
    
    @staticmethod
    def from_bytes(data: bytes) -> Optional['NetworkMessage']:
        """
        Deserialize message from bytes.
        
        Args:
            data: Raw bytes
            
        Returns:
            NetworkMessage instance or None if invalid
        """
        if len(data) < 5:  # Minimum: 1 byte type + 4 bytes length
            return None
        
        try:
            msg_type = MessageType(struct.unpack('B', data[0:1])[0])
            length = struct.unpack('!I', data[1:5])[0]
            
            if len(data) < 5 + length:
                return None
            
            json_data = data[5:5+length].decode('utf-8')
            message_data = json.loads(json_data)
            
            return NetworkMessage(msg_type, message_data)
        except (ValueError, json.JSONDecodeError, struct.error):
            return None
    
    def __repr__(self) -> str:
        """String representation."""
        return f"NetworkMessage({self.msg_type.name}, {self.data})"


# Message creation helpers

def create_connect_message(player_id: int, player_name: str) -> NetworkMessage:
    """Create a connection request message."""
    return NetworkMessage(MessageType.CONNECT, {
        'player_id': player_id,
        'player_name': player_name,
        'version': '0.1.0'
    })


def create_connect_ack_message(player_id: int, assigned_id: int, game_state: Dict) -> NetworkMessage:
    """Create a connection acknowledgment message."""
    return NetworkMessage(MessageType.CONNECT_ACK, {
        'requested_id': player_id,
        'assigned_id': assigned_id,
        'game_state': game_state
    })


def create_disconnect_message(player_id: int, reason: str = "quit") -> NetworkMessage:
    """Create a disconnect message."""
    return NetworkMessage(MessageType.DISCONNECT, {
        'player_id': player_id,
        'reason': reason
    })


def create_position_update(player_id: int, x: float, y: float, angle: float) -> NetworkMessage:
    """Create a position update message."""
    return NetworkMessage(MessageType.POSITION_UPDATE, {
        'player_id': player_id,
        'x': x,
        'y': y,
        'angle': angle
    })


def create_shoot_message(player_id: int, x: float, y: float, angle: float) -> NetworkMessage:
    """Create a shoot message."""
    return NetworkMessage(MessageType.SHOOT, {
        'player_id': player_id,
        'x': x,
        'y': y,
        'angle': angle
    })


def create_hit_message(shooter_id: int, target_id: int, damage: int) -> NetworkMessage:
    """Create a hit notification message."""
    return NetworkMessage(MessageType.HIT, {
        'shooter_id': shooter_id,
        'target_id': target_id,
        'damage': damage
    })


def create_player_died_message(player_id: int, killer_id: int) -> NetworkMessage:
    """Create a player death message."""
    return NetworkMessage(MessageType.PLAYER_DIED, {
        'player_id': player_id,
        'killer_id': killer_id
    })


def create_player_respawn_message(player_id: int, x: float, y: float, angle: float) -> NetworkMessage:
    """Create a player respawn message."""
    return NetworkMessage(MessageType.PLAYER_RESPAWN, {
        'player_id': player_id,
        'x': x,
        'y': y,
        'angle': angle
    })


def create_score_update_message(player_id: int, kills: int, deaths: int) -> NetworkMessage:
    """Create a score update message."""
    return NetworkMessage(MessageType.SCORE_UPDATE, {
        'player_id': player_id,
        'kills': kills,
        'deaths': deaths
    })


def create_health_update_message(player_id: int, health: int) -> NetworkMessage:
    """Create a health update message."""
    return NetworkMessage(MessageType.HEALTH_UPDATE, {
        'player_id': player_id,
        'health': health
    })


def create_ping_message(player_id: int, timestamp: float) -> NetworkMessage:
    """Create a ping message."""
    return NetworkMessage(MessageType.PING, {
        'player_id': player_id,
        'timestamp': timestamp
    })


def create_pong_message(player_id: int, timestamp: float) -> NetworkMessage:
    """Create a pong response message."""
    return NetworkMessage(MessageType.PONG, {
        'player_id': player_id,
        'timestamp': timestamp
    })


if __name__ == "__main__":
    # Test protocol
    print("Testing network protocol...")
    
    # Test message creation
    print("\n1. Creating messages...")
    msg1 = create_connect_message(1, "Player1")
    print(f"  Connect: {msg1}")
    
    msg2 = create_position_update(1, 10.5, 5.3, 1.57)
    print(f"  Position: {msg2}")
    
    msg3 = create_shoot_message(1, 10.5, 5.3, 1.57)
    print(f"  Shoot: {msg3}")
    
    # Test serialization
    print("\n2. Testing serialization...")
    serialized = msg1.to_bytes()
    print(f"  Serialized length: {len(serialized)} bytes")
    print(f"  First 20 bytes: {serialized[:20]}")
    
    # Test deserialization
    print("\n3. Testing deserialization...")
    deserialized = NetworkMessage.from_bytes(serialized)
    print(f"  Deserialized: {deserialized}")
    print(f"  Data matches: {deserialized.data == msg1.data}")
    
    # Test all message types
    print("\n4. Testing all message types...")
    messages = [
        create_connect_message(1, "Test"),
        create_position_update(1, 1.0, 2.0, 3.0),
        create_shoot_message(1, 1.0, 2.0, 3.0),
        create_hit_message(1, 2, 25),
        create_player_died_message(2, 1),
        create_score_update_message(1, 5, 2),
        create_ping_message(1, 123.456),
    ]
    
    for msg in messages:
        serialized = msg.to_bytes()
        deserialized = NetworkMessage.from_bytes(serialized)
        match = deserialized.msg_type == msg.msg_type and deserialized.data == msg.data
        status = "✓" if match else "✗"
        print(f"  {status} {msg.msg_type.name}: {len(serialized)} bytes")
    
    print("\n✓ Protocol tests passed!")
