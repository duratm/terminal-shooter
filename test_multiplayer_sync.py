#!/usr/bin/env python3
"""
Test multiplayer sync - verifies both clients receive each other's updates.
"""

import sys
import os
import socket
import time
import threading

sys.path.insert(0, os.path.dirname(__file__))

from src.network.server import GameServer
from src.network.client import GameClient
from src.network.protocol import NetworkMessage, MessageType

def test_multiplayer_sync():
    """Test that two clients can see each other."""
    print("\n" + "="*60)
    print("🧪 Multiplayer Sync Test")
    print("="*60 + "\n")
    
    # Start server
    print("Step 1: Starting server...")
    server = GameServer(host='127.0.0.1', port=5556, max_players=8)
    if not server.start():
        print("❌ Failed to start server")
        return False
    print("✅ Server started\n")
    
    time.sleep(0.5)
    
    # Connect client 1
    print("Step 2: Connecting client 1...")
    client1 = GameClient(server_host='127.0.0.1', server_port=5556, player_name='Alice')
    if not client1.connect():
        print("❌ Client 1 failed to connect")
        server.stop()
        return False
    print(f"✅ Client 1 connected (ID: {client1.player_id})\n")
    
    time.sleep(0.5)
    
    # Connect client 2
    print("Step 3: Connecting client 2...")
    client2 = GameClient(server_host='127.0.0.1', server_port=5556, player_name='Bob')
    if not client2.connect():
        print("❌ Client 2 failed to connect")
        client1.disconnect()
        server.stop()
        return False
    print(f"✅ Client 2 connected (ID: {client2.player_id})\n")
    
    time.sleep(0.5)
    
    # Client 1 moves
    print("Step 4: Client 1 sends position update...")
    client1.local_player.x = 10.0
    client1.local_player.y = 10.0
    client1.send_position_update(10.0, 10.0, 0.5)
    print("✅ Position sent\n")
    
    # Client 2 moves
    print("Step 5: Client 2 sends position update...")
    client2.local_player.x = 15.0
    client2.local_player.y = 15.0
    client2.send_position_update(15.0, 15.0, 1.5)
    print("✅ Position sent\n")
    
    # Wait for server to broadcast
    print("Step 6: Waiting for server to broadcast updates...")
    time.sleep(1.0)
    
    # Process messages on both clients
    print("Step 7: Processing received messages...")
    client1.process_messages()
    client2.process_messages()
    
    # Check results
    print("\n" + "="*60)
    print("📊 Results")
    print("="*60)
    
    print(f"\nClient 1 (ID: {client1.player_id}):")
    print(f"   Other players: {list(client1.other_players.keys())}")
    if client1.other_players:
        for pid, p in client1.other_players.items():
            print(f"   - Player {pid}: ({p.x:.1f}, {p.y:.1f})")
    
    print(f"\nClient 2 (ID: {client2.player_id}):")
    print(f"   Other players: {list(client2.other_players.keys())}")
    if client2.other_players:
        for pid, p in client2.other_players.items():
            print(f"   - Player {pid}: ({p.x:.1f}, {p.y:.1f})")
    
    # Verify
    success = True
    
    # Client 1 should see client 2
    if client2.player_id in client1.other_players:
        print(f"\n✅ Client 1 can see Client 2")
    else:
        print(f"\n❌ Client 1 cannot see Client 2")
        success = False
    
    # Client 2 should see client 1
    if client1.player_id in client2.other_players:
        print(f"✅ Client 2 can see Client 1")
    else:
        print(f"❌ Client 2 cannot see Client 1")
        success = False
    
    # Cleanup
    print("\nCleaning up...")
    client1.disconnect()
    client2.disconnect()
    server.stop()
    
    print("\n" + "="*60)
    if success:
        print("✅ ALL TESTS PASSED - Multiplayer sync is working!")
    else:
        print("❌ TESTS FAILED - Multiplayer sync has issues")
    print("="*60 + "\n")
    
    return success

if __name__ == '__main__':
    success = test_multiplayer_sync()
    sys.exit(0 if success else 1)
