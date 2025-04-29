#!/bin/bash

set -e

echo -e "\e]2;UVR5 UI Updater\a"

REPO_URL="https://github.com/Eddycrack864/UVR5-UI"
INSTALL_DIR="$PWD"
ENV_DIR="$INSTALL_DIR/env"
CONDA_EXE="$HOME/miniconda3/bin/conda"

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

if ! command_exists "$CONDA_EXE"; then
  error_exit "Miniconda is not installed. Please run the installer first."
fi

echo "Updating Conda environment..."
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate "$ENV_DIR" || error_exit "Failed to activate conda environment."

echo "Checking for updated dependencies..."
pip install -r "$INSTALL_DIR/requirements.txt" || error_exit "Failed to update dependencies."

conda deactivate || error_exit "Failed to deactivate conda environment."
echo "Conda environment updated successfully."
echo

echo "Update Complete!"
echo "UVR5 UI has been updated to the latest version."
read -p "Press Enter to exit..."