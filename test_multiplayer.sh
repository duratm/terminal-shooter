#!/bin/bash

# Terminal Shooter Multiplayer Test Script
# This helps diagnose multiplayer connection issues

echo "=========================================="
echo "Terminal Shooter - Multiplayer Test"
echo "=========================================="
echo ""

# Check if terminal is in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Run this from terminal-shooter/ directory"
    exit 1
fi

echo "Choose test mode:"
echo "1) Start debug server (shows all events)"
echo "2) Start normal server"
echo "3) Connect as client to localhost"
echo "4) Run connection diagnostic"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        echo ""
        echo "🔍 Starting DEBUG SERVER on port 5555..."
        echo "This will show all events the server receives."
        echo ""
        python3 src/network/debug_server.py
        ;;
    2)
        echo ""
        echo "🎮 Starting NORMAL SERVER on port 5555..."
        echo ""
        python3 -m src.main --host
        ;;
    3)
        echo ""
        echo "🔌 Connecting to localhost:5555 as client..."
        echo ""
        python3 -m src.main --join localhost
        ;;
    4)
        echo ""
        echo "🔧 Running connection diagnostic..."
        echo ""
        
        # Check if port is in use
        if lsof -Pi :5555 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            echo "✅ Server is running on port 5555"
            PID=$(lsof -Pi :5555 -sTCP:LISTEN -t)
            echo "   PID: $PID"
        else
            echo "❌ No server running on port 5555"
            echo "   Start server first with: ./test_multiplayer.sh (option 1 or 2)"
        fi
        echo ""
        
        # Check network connectivity
        echo "Testing localhost connection..."
        if nc -z localhost 5555 2>/dev/null; then
            echo "✅ Can connect to localhost:5555"
        else
            echo "⚠️  Cannot connect to localhost:5555"
            echo "   Make sure server is running"
        fi
        echo ""
        
        # Show network interfaces
        echo "Available network interfaces:"
        ip -4 addr show | grep -E '^[0-9]|inet ' | grep -v '127.0.0.1'
        echo ""
        
        echo "Diagnostic complete!"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
