#!/bin/bash

set -e

echo -e "\e]2;UVR5 UI Updater\a"

REPO_URL="https://github.com/Eddycrack864/UVR5-UI"

if ! command -v git &> /dev/null; then
    echo "Error: Git is not installed. Please install Git and try again."
    read -p "Press Enter to exit..."
    exit 1
fi

if [ ! -d ".git" ]; then
    git init
    git remote add origin "$REPO_URL"
fi

git fetch origin
if [ $? -ne 0 ]; then
    echo "Error: Failed to fetch updates. Check your internet connection or Git configuration."
    read -p "Press Enter to exit..."
    exit 1
fi

git reset --hard origin/main
if [ $? -ne 0 ]; then
    echo "Error: Failed to reset repository. Check your Git configuration or repository status."
    read -p "Press Enter to exit..."
    exit 1
fi

echo "Update Complete!"
echo

read -p "Press Enter to exit..."