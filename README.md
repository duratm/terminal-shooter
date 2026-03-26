# Terminal Shooter

A first-person shooter game built entirely for the terminal using ASCII graphics and Python. Experience classic FPS gameplay with raycasting rendering, smooth movement, and shooting mechanics - all in your terminal!

## 🎮 Features

### ✅ Fully Implemented
- **3D Raycasting Engine**: Pseudo-3D first-person view using ASCII characters
- **Smooth Movement**: WASD controls with collision detection
- **Camera Control**: Arrow keys for looking around
- **Shooting Mechanics**: Fire projectiles with realistic physics
- **Health & Ammo System**: Track your status with visual feedback
- **HUD Display**: Health bar, ammo counter, score, position, and FPS
- **Minimap**: Real-time top-down view with other players
- **Crosshair**: Aiming reticle for precision shooting
- **Dynamic Messages**: Visual feedback for actions
- **Arena Map**: Pre-built arena with obstacles and spawn points
- **LAN Multiplayer**: Host/join games on local network
- **Arena Deathmatch**: Real-time multiplayer combat
- **Score Tracking**: Kills, deaths, and leaderboard
- **Player Synchronization**: See other players move and shoot in real-time

### 🚧 Coming Soon
- **Enhanced UI**: Main menu and lobby system
- **Multiple Maps**: Additional arenas to explore
- **More Weapons**: Variety of weapons with different stats
- **Performance Optimization**: Even smoother gameplay
- **Audio Feedback**: Terminal beeps and effects

## 📋 Requirements

- **Python 3.8+**
- **Unix-like terminal** (Linux/macOS) or Windows Terminal
- **Terminal with UTF-8 and 256-color support**
- **Recommended terminal size**: 120x40 characters (minimum 80x24)

## 🚀 Quick Start

### Installation

```bash
# Navigate to the project directory
cd terminal-shooter

# Method 1: Use the run script (easiest)
chmod +x run.sh

# Solo mode
./run.sh --solo

# Host multiplayer
./run.sh --host

# Method 2: Manual setup
python3 -m venv venv
source venv/bin/activate  # On Linux/macOS
# or: venv\Scripts\activate  # On Windows
pip install -r requirements.txt

# On Windows, you'll also need:
pip install windows-curses
```

### Play Modes

```bash
# Solo Mode - Play offline
python -m src.main --solo

# Host Multiplayer - Start a server and play
python -m src.main --host

# Join Multiplayer - Connect to a friend's game
python -m src.main --join <host_ip>

# Example: Join localhost
python -m src.main --join localhost

# Example: Join specific IP
python -m src.main --join 192.168.1.100

# Or use the run script
./run.sh --solo
./run.sh --host
./run.sh --join 192.168.1.100
```

### Multiplayer Setup (LAN)

**To Host a Game:**
1. Find your IP address:
   - Linux/Mac: `ip addr show` or `ifconfig`
   - Windows: `ipconfig`
2. Run: `python -m src.main --host`
3. Share your IP with friends on the same network
4. They connect with: `python -m src.main --join <your_ip>`

**To Join a Game:**
1. Get the host's IP address
2. Run: `python -m src.main --join <host_ip>`
3. Start playing!

## 🎯 Controls

| Key | Action |
|-----|--------|
| **W** | Move forward |
| **A** | Strafe left |
| **S** | Move backward |
| **D** | Strafe right |
| **←/→** | Rotate camera left/right |
| **Space** | Shoot |
| **R** | Reload weapon |
| **Q** or **ESC** | Quit game |

## 📊 HUD Elements

The game displays comprehensive information:
- **Health Bar**: Visual health indicator (top of status line)
- **Ammo Counter**: Current/max ammo display
- **K/D Score**: Kills/Deaths and total score
- **Position**: Your current coordinates in the map
- **Angle**: Camera rotation in degrees
- **FPS**: Frames per second
- **Minimap**: Top-right corner shows your position (@) and walls (#)
- **Crosshair**: Center screen (+) for aiming
- **Messages**: Top-left shows recent actions

## 🗺️ Map Features

The default arena includes:
- **24x23 tile arena** with walls and obstacles
- **2 spawn points** for player starts
- **Symmetrical design** for fair gameplay
- **Strategic cover** with interior walls

## 🛠️ Technical Details

### Architecture
- **Rendering**: Custom raycasting engine with ASCII output
- **Graphics**: Depth-based character shading (█ ▓ ▒ ░ ·)
- **Physics**: Collision detection with circular hitboxes
- **Networking**: Protocol defined (server/client in development)

### Project Structure
```
terminal-shooter/
├── src/
│   ├── main.py           # Entry point
│   ├── game.py           # Main game loop
│   ├── renderer.py       # Raycasting renderer
│   ├── player.py         # Player class
│   ├── map.py            # Map and collision
│   ├── weapons.py        # Weapons and projectiles
│   ├── network/
│   │   └── protocol.py   # Network protocol
│   └── ui/
│       └── hud.py        # HUD rendering
├── assets/
│   └── maps/
│       └── arena01.txt   # Default arena
├── requirements.txt
├── README.md
└── run.sh
```

### Code Statistics
- **~1,800 lines** of Python code
- **11 Python modules**
- **5 core systems**: Rendering, Physics, Player, Weapons, UI

## 🎯 Gameplay Tips

1. **Movement**: Use WASD for strafing - you can move and look independently
2. **Aiming**: The crosshair shows exactly where you're aiming
3. **Ammo Management**: Watch your ammo counter and reload (R) when safe
4. **Minimap**: Use the minimap to see other players (P) and navigate
5. **Walls**: Projectiles stop at walls, use them for cover
6. **FPS**: If performance is low, try a smaller terminal window
7. **Multiplayer**: Coordinate with teammates or hunt enemies on the minimap
8. **Scoring**: Your K/D ratio is displayed - try to keep it positive!

## 🐛 Troubleshooting

### Game won't start
- Ensure Python 3.8+ is installed: `python3 --version`
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

### Display issues
- Increase terminal size to at least 80x24
- Enable UTF-8 encoding in your terminal
- Try a different terminal emulator (recommended: GNOME Terminal, iTerm2, Windows Terminal)

### "curs_set() returned ERR"
- This is usually harmless and the game should still work
- Some terminals don't support cursor visibility control

### Performance issues
- Reduce terminal window size
- Close other applications
- Try a faster terminal emulator

## 🎯 Development Roadmap

### Phase 1: Core Engine ✅ COMPLETE
- [x] Project structure
- [x] Map system with collision
- [x] Raycasting algorithm
- [x] ASCII renderer
- [x] Testing framework

### Phase 2: Single-Player ✅ COMPLETE
- [x] Player class with state management
- [x] Movement and camera controls
- [x] Weapon and projectile system
- [x] Shooting mechanics
- [x] HUD with health, ammo, and score

### Phase 3: Networking ✅ COMPLETE
- [x] Network protocol design
- [x] Game server implementation
- [x] Client networking
- [x] State synchronization
- [x] Multiplayer testing

### Phase 4: Multiplayer ✅ COMPLETE
- [x] Sync player positions
- [x] Sync shooting and hits
- [x] Spawn system
- [x] Scoring and leaderboard
- [x] Handle disconnections

### Phase 5: Polish (Future)
- [ ] Main menu
- [ ] Lobby system
- [ ] Audio feedback
- [ ] Performance optimization
- [ ] Additional maps
- [ ] Documentation

## 🤝 Contributing

This is a learning project demonstrating:
- Terminal graphics with curses
- Raycasting algorithms
- Game physics and collision
- Network protocol design
- Real-time multiplayer architecture

Feel free to explore the code and learn from it!

## 📝 License

MIT License - feel free to modify and distribute.

## 🎉 Credits

Built as a demonstration of terminal-based game development using Python.

---

**Enjoy the game! Press Q at any time to quit.**

For issues or questions, check the troubleshooting section above.

## 🌐 Multiplayer Guide

### Network Requirements
- All players must be on the same LAN (Local Area Network)
- Host must allow incoming connections on port 5555 (or custom port)
- Firewall may need to allow Python/terminal-shooter

### Hosting a Game

1. **Find Your IP Address:**
   ```bash
   # Linux/macOS
   ip addr show | grep inet
   # or
   ifconfig
   
   # Windows
   ipconfig
   ```

2. **Start the Server:**
   ```bash
   python -m src.main --host
   ```

3. **Share Your IP:**
   - Tell friends your IP address (e.g., 192.168.1.100)
   - They join with: `python -m src.main --join 192.168.1.100`

4. **Start Playing:**
   - Host automatically joins as a player
   - Other players can connect and join the battle

### Joining a Game

1. **Get the Host's IP Address**

2. **Connect:**
   ```bash
   python -m src.main --join <host_ip>
   
   # Examples:
   python -m src.main --join 192.168.1.100
   python -m src.main --join localhost  # If hosting on same machine
   ```

3. **Start Playing:**
   - You'll spawn in the arena
   - See other players on minimap (P markers)
   - Battle for the highest score!

### Multiplayer Features
- **Up to 8 players** (configurable)
- **Real-time synchronization** of positions and actions
- **Server-authoritative** hit detection (no cheating!)
- **Automatic respawn** after 3 seconds
- **Live score tracking** (K/D ratio)
- **Player indicators** on minimap

### Troubleshooting Multiplayer

**Can't connect?**
- Verify host IP address is correct
- Check both computers are on same network
- Try: `ping <host_ip>` to test connection
- Firewall may be blocking port 5555
- Try custom port: `--port 5556`

**Lag or stuttering?**
- Check network quality (ping times)
- Close other network-heavy applications
- Reduce number of players
- Host on computer with better network connection

**Connection drops?**
- Network instability
- Host closed game
- Timeout (10 seconds without updates)

