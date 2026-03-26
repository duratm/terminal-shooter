#!/bin/bash
# Activate virtual environment
source "$(dirname "$0")/venv/bin/activate"

# Run game in Kitty graphics mode
python3 -m src.main --solo --graphics kitty "$@"
