#!/bin/bash

set -e

echo -e "\e]2;UVR5 UI\a"

if [ ! -d "env" ]; then
    echo "Please run 'UVR5-UI-installer.sh' first to set up the environment"
    read -p "Press Enter to exit..."
    exit 1
fi

env/bin/python app.py