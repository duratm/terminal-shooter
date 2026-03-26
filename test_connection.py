#!/usr/bin/env python3
"""
Test client connection to debug where the timeout occurs.
"""

import socket
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from src.network.protocol import create_connect_message, NetworkMessage, MessageType

def test_connection():
    """Test connecting to the server step by step."""
    print("\n" + "="*60)
    print("🔍 Testing Client Connection")
    print("="*60 + "\n")
    
    host = 'localhost'
    port = 5555
    
    # Step 1: Create socket
    print("Step 1: Creating TCP socket...")
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(5.0)
        print("✅ Socket created")
    except Exception as e:
        print(f"❌ Failed to create socket: {e}")
        return False
    
    # Step 2: Connect
    print(f"\nStep 2: Connecting to {host}:{port}...")
    try:
        tcp_socket.connect((host, port))
        print("✅ Connected to server")
    except socket.timeout:
        print("❌ Connection timed out")
        print("   Server might not be running or not accepting connections")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Step 3: Send connect message
    print("\nStep 3: Sending CONNECT message...")
    try:
        connect_msg = create_connect_message(0, "TestPlayer")
        print(f"   Message type: {connect_msg.msg_type}")
        print(f"   Message data: {connect_msg.data}")
        
        bytes_sent = tcp_socket.send(connect_msg.to_bytes())
        print(f"✅ Sent {bytes_sent} bytes")
    except Exception as e:
        print(f"❌ Failed to send: {e}")
        return False
    
    # Step 4: Receive acknowledgment
    print("\nStep 4: Waiting for CONNECT_ACK...")
    try:
        tcp_socket.settimeout(10.0)  # Give server time to respond
        data = tcp_socket.recv(1024)
        print(f"✅ Received {len(data)} bytes")
        
        ack_msg = NetworkMessage.from_bytes(data)
        if ack_msg:
            print(f"   Message type: {ack_msg.msg_type}")
            print(f"   Message data: {ack_msg.data}")
            
            if ack_msg.msg_type == MessageType.CONNECT_ACK:
                print("✅ Connection successful!")
                player_id = ack_msg.data.get('assigned_id')
                print(f"   Assigned player ID: {player_id}")
                return True
            else:
                print(f"⚠️  Unexpected message type: {ack_msg.msg_type}")
                return False
        else:
            print("❌ Failed to parse response")
            return False
            
    except socket.timeout:
        print("❌ Timeout waiting for response")
        print("   Server received connection but didn't respond")
        return False
    except Exception as e:
        print(f"❌ Failed to receive: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        tcp_socket.close()

if __name__ == '__main__':
    success = test_connection()
    
    print("\n" + "="*60)
    if success:
        print("✅ Connection test PASSED")
        print("\nThe connection works! The issue might be:")
        print("1. Client starting before server is ready")
        print("2. Different error in the actual game client")
        print("3. Timing issue")
    else:
        print("❌ Connection test FAILED")
        print("\nTroubleshooting:")
        print("1. Make sure debug server is running:")
        print("   python3 src/network/debug_server.py")
        print("2. Check if port 5555 is listening:")
        print("   lsof -i :5555")
        print("3. Try killing existing server and restarting:")
        print("   pkill -f debug_server.py")
    print("="*60 + "\n")
    
    sys.exit(0 if success else 1)
