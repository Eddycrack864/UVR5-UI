#!/bin/bash

set -e

echo -e "\e]2;UVR5 UI Updater\a"

REPO_URL="https://github.com/Eddycrack864/UVR5-UI"
INSTALL_DIR="$(pwd)"
ENV_DIR="$INSTALL_DIR/env"
PYTHON_EXE="$ENV_DIR/bin/python"

error_exit() {
    echo "Error: $1"
    read -p "Press Enter to exit..."
    exit 1
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

if ! command_exists git; then
    error_exit "Git is not installed. Please install Git and try again."
fi

if [ ! -d ".git" ]; then
    git init
    git remote add origin "$REPO_URL"
    echo "Git repository initialized."
fi

git fetch origin || error_exit "Failed to fetch updates. Check your internet connection or Git configuration."
git reset --hard origin/main || error_exit "Failed to reset repository. Check your Git configuration or repository status."

echo "Code updated successfully."
echo

if [ ! -f "$PYTHON_EXE" ]; then
    error_exit "Python environment not found at '$ENV_DIR'. Please run the installer first. If you are using the pre-compiled version, you cannot fully update UVR5 UI with this script. Please download the latest version from GitHub."
fi

echo "Updating Conda environment..."
echo "Checking for updated dependencies..."

"$PYTHON_EXE" -m pip install --upgrade -r "$INSTALL_DIR/requirements.txt" || error_exit "Failed to update dependencies."

echo "Conda environment updated successfully."
echo

echo "Update Complete!"
echo "UVR5 UI has been updated to the latest version."
read -p "Press Enter to exit..."