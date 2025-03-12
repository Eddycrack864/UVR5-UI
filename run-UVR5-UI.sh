#!/bin/bash

set -e

echo -e "\e]2;UVR5 UI\a"

if [ -d "env" ]; then
    env/bin/python app.py --open
else
    echo "Searching for global python and dependencies..."
    if command -v python &> /dev/null; then
        python app.py --open
    else
        echo "Error: Python not found. Please install UVR5 UI globally or run 'UVR5-UI-installer.bat' to set up the environment."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi