"""
Main entry point for Terminal Shooter game.
Handles command-line arguments and game initialization.
"""

import sys
import argparse
import curses
import threading

from .game import start_game
from .map import create_default_map, Map
from .network.server import GameServer
from .network.client import GameClient


def print_welcome():
    """Print welcome banner."""
    print("=" * 70)
    print(" " * 20 + "TERMINAL SHOOTER")
    print(" " * 15 + "ASCII First-Person Shooter")
    print("=" * 70)


def print_controls():
    """Print control instructions."""
    print("\n📋 CONTROLS:")
    print("  WASD        - Move (forward, left, back, right)")
    print("  Arrow Keys  - Rotate camera / Look around")
    print("  Space       - Shoot")
    print("  R           - Reload")
    print("  [ / ]       - Decrease / Increase mouse sensitivity")
    print("  Q / ESC     - Quit game")
    
    print("\n🎯 HUD ELEMENTS:")
    print("  Health Bar  - Shows your current health")
    print("  Ammo        - Current/max ammunition")
    print("  Minimap     - Top-right corner (@ = you, # = walls)")
    print("  Crosshair   - Center screen (+) for aiming")
    print("  Status      - Bottom line shows all stats")


def main():
    """Main entry point for the game."""
    parser = argparse.ArgumentParser(
        description="Terminal Shooter - ASCII FPS Game",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --solo          Play in solo/test mode
  python -m src.main --host          Host a multiplayer game (coming soon)
  python -m src.main --join 192.168.1.100   Join a game (coming soon)
        """
    )
    parser.add_argument('--host', action='store_true', help='Host a multiplayer game (not yet implemented)')
    parser.add_argument('--join', type=str, metavar='IP', help='Join a game at the specified IP (not yet implemented)')
    parser.add_argument('--port', type=int, default=5555, help='Port to use (default: 5555)')
    parser.add_argument('--solo', action='store_true', help='Play in solo/test mode')
    parser.add_argument('--test', action='store_true', help='Run in test mode (same as --solo)')
    parser.add_argument('--skip-intro', action='store_true', help='Skip intro messages')
    parser.add_argument('--sensitivity', type=float, default=0.15, help='Mouse sensitivity (default: 0.15)')
    parser.add_argument('--graphics', choices=['ascii', 'kitty'], default='ascii', help='Graphics mode (ascii or kitty)')
    parser.add_argument('--native-input', action='store_true', help='Use pynput for native keyboard handling (requires local execution)')
    parser.add_argument('--evdev', action='store_true', help='Use evdev for direct input (requires permissions, good for Wayland)')
    
    args = parser.parse_args()
    
    # Solo/test mode
    if args.test or args.solo:
        if not args.skip_intro:
            print_welcome()
            print("\n🎯 Starting SOLO MODE...")
            print_controls()
            print(f"  Mouse Sens  - {args.sensitivity} (Use [ and ] to adjust)")
            print(f"  Graphics    - {args.graphics.upper()}")
            print(f"  Native Inp  - {'ENABLED' if args.native_input else 'DISABLED'}")
            print(f"  Evdev       - {'ENABLED' if args.evdev else 'DISABLED'}")
            print("\n" + "=" * 70)
            print("💡 TIP: Make your terminal fullscreen for the best experience!")
            print("=" * 70)
            print("\nPress ENTER to start the game...")
            try:
                input()
            except KeyboardInterrupt:
                print("\n\nCancelled.")
                return 0
        
        try:
            game_map = create_default_map()
            curses.wrapper(start_game, game_map=game_map, sensitivity=args.sensitivity, graphics_mode=args.graphics, native_input=args.native_input, use_evdev=args.evdev)
        except KeyboardInterrupt:
            print("\n\n🎮 Game interrupted. Thanks for playing!")
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        print("\n" + "=" * 70)
        print(" " * 22 + "GAME OVER")
        print(" " * 17 + "Thanks for playing!")
        print("=" * 70)
        return 0
    
    # Multiplayer hosting
    elif args.host:
        print_welcome()
        print(f"\n🌐 MULTIPLAYER HOSTING")
        print("=" * 70)
        
        # Start server in background thread
        server = GameServer('0.0.0.0', args.port)
        
        if not server.start():
            return 1
        
        print(f"\n✅ Server running on port {args.port}")
        print("   Waiting for players to connect...")
        print("\n💡 To join this game from another terminal:")
        print(f"   python -m src.main --join localhost")
        print("\n💡 From another computer on your LAN:")
        print(f"   python -m src.main --join <your_ip_address>")
        
        # Connect as host player
        print("\n🎮 Starting game as host...")
        if not args.skip_intro:
            print_controls()
            print("\nPress ENTER to start playing...")
            try:
                input()
            except KeyboardInterrupt:
                print("\n\nCancelled.")
                server.stop()
                return 0
        
        # Connect to own server
        client = GameClient('localhost', args.port, "Host")
        if not client.connect():
            print("❌ Failed to connect to own server")
            server.stop()
            return 1
        
        try:
            game_map = create_default_map()
            curses.wrapper(start_game, game_map, client, sensitivity=args.sensitivity, graphics_mode=args.graphics, native_input=args.native_input, use_evdev=args.evdev)
        except KeyboardInterrupt:
            print("\n\n🎮 Game interrupted.")
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            client.disconnect()
            server.stop()
        
        print("\n" + "=" * 70)
        print(" " * 22 + "GAME OVER")
        print(" " * 17 + "Thanks for playing!")
        print("=" * 70)
        return 0
    
    # Multiplayer joining
    elif args.join:
        print_welcome()
        print(f"\n🔗 MULTIPLAYER JOIN")
        print("=" * 70)
        print(f"   Connecting to {args.join}:{args.port}...")
        
        # Connect to server
        client = GameClient(args.join, args.port, "Player")
        if not client.connect():
            print(f"\n❌ Failed to connect to server at {args.join}:{args.port}")
            print("\n💡 Troubleshooting:")
            print("   • Check that the host is running")
            print("   • Verify the IP address is correct")
            print("   • Check firewall settings")
            print("   • Make sure you're on the same network (LAN)")
            return 1
        
        if not args.skip_intro:
            print_controls()
            print("\nPress ENTER to start playing...")
            try:
                input()
            except KeyboardInterrupt:
                print("\n\nCancelled.")
                client.disconnect()
                return 0
        
        try:
            game_map = create_default_map()
            curses.wrapper(start_game, game_map, client, sensitivity=args.sensitivity, graphics_mode=args.graphics, native_input=args.native_input, use_evdev=args.evdev)
        except KeyboardInterrupt:
            print("\n\n🎮 Game interrupted.")
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            client.disconnect()
        
        print("\n" + "=" * 70)
        print(" " * 22 + "GAME OVER")
        print(" " * 17 + "Thanks for playing!")
        print("=" * 70)
        return 0
    
    # No arguments - show help
    else:
        print_welcome()
        print("\n🎮 WELCOME TO TERMINAL SHOOTER!")
        print("=" * 70)
        print("\n✅ AVAILABLE NOW:")
        print("  • Solo Mode - Explore the arena and test your skills")
        print("  • Multiplayer Mode - LAN deathmatch with friends!")
        print("  • Full 3D raycasting engine with ASCII graphics")
        print("  • Smooth movement and shooting mechanics")
        print("  • Health, ammo, and HUD system")
        print("  • Minimap and crosshair")
        
        print("\n🌐 MULTIPLAYER:")
        print("  • Host a game and play with friends on your network")
        print("  • Real-time arena deathmatch")
        print("  • See other players on minimap")
        print("  • Score tracking (kills/deaths)")
        
        print("\n🚧 COMING SOON:")
        print("  • Enhanced multiplayer features")
        print("  • Leaderboard display")
        print("  • Multiple maps")
        print("  • More weapons")
        
        print("\n🚀 GET STARTED:")
        print("  python -m src.main --solo           # Play solo")
        print("  python -m src.main --host           # Host multiplayer game")
        print("  python -m src.main --join <IP>      # Join a friend's game")
        print("  python -m src.main --help           # See all options")
        
        print("\n💡 TIPS:")
        print("  • Use a fullscreen terminal for best experience")
        print("  • Minimum terminal size: 80x24")
        print("  • Recommended size: 120x40 or larger")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
