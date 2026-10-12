#!/bin/bash

set -e

echo -e "\e]2;UVR5 UI Updater\a"

REPO_URL="https://github.com/Eddycrack864/UVR5-UI"
INSTALL_DIR="$(pwd)"
ENV_DIR="$INSTALL_DIR/env"
PYTHON_EXE="$ENV_DIR/bin/python"

pause_if_interactive() {
    if [ -t 0 ]; then
        read -r -p "$1"
    fi
}

error_exit() {
    echo "Error: $1"
    pause_if_interactive "Press Enter to exit..."
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

# Older versions kept user preferences in the tracked assets/config.json, which the reset below deletes.
if [ -f "assets/config.json" ] && [ ! -f "user_data/config.json" ]; then
    mkdir -p user_data
    cp "assets/config.json" "user_data/config.json"
    echo "Your preferences were backed up to user_data/config.json"
fi

if [ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then
    echo "WARNING: These local changes to UVR5 UI files will be discarded by the update:"
    git status --short --untracked-files=no
    echo "Your settings in user_data/ and your models are not affected."
    pause_if_interactive "Press Enter to continue or Ctrl+C to cancel..."
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
pause_if_interactive "Press Enter to exit..."
