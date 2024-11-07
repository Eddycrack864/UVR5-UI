#!/bin/bash

set -e

echo -e "\e]2;UVR5 UI Updater\a"

REPO_URL="https://github.com/Eddycrack864/UVR5-UI"

if [ ! -d ".git" ]; then
    git init
    git remote add origin "$REPO_URL"
fi

git fetch origin
git reset --hard origin/main

echo "Update Complete!"
echo

read -p "Press Enter to exit..."