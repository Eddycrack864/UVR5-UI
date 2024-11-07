#!/bin/bash

echo "Welcome to the UVR5 UI Installer!"
echo

INSTALL_DIR="$(pwd)"
MINICONDA_DIR="$HOME/miniconda3"
ENV_DIR="$INSTALL_DIR/env"
MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py310_24.9.2-0-Linux-x86_64.sh"
CONDA_EXE="$MINICONDA_DIR/bin/conda"

echo -e "\e]2;UVR5 UI Installer\a"

check_privileges() {
    if [ "$(id -u)" -eq 0 ]; then
        echo "ERROR: This script must not be run with sudo/root privileges"
        echo "Please run it as a normal user without sudo"
        read -p "Press Enter to exit..."
        exit 1
    fi
    echo "The script is running without root privileges, continuing..."
    echo
}

cleanup() {
    echo "Cleaning up unnecessary files..."
    rm -f *.bat
    echo "Cleanup complete"
    echo
}

install_miniconda() {
    if [ -f "$CONDA_EXE" ]; then
        echo "Miniconda already installed. Skipping installation..."
        return 0
    fi

    echo "Miniconda not found. Starting download and installation..."
    if ! wget "$MINICONDA_URL" -O miniconda.sh; then
        echo "Download failed. Please check your internet connection and try again"
        exit 1
    fi

    bash miniconda.sh -b -p "$MINICONDA_DIR"
    if [ $? -ne 0 ]; then
        echo "Miniconda installation failed"
        exit 1
    fi

    rm miniconda.sh
    echo "Miniconda installation complete"
    echo

    export PATH="$MINICONDA_DIR/condabin:$PATH"
    echo "Added Miniconda to PATH"
}

create_conda_env() {
    echo "Creating Conda environment..."
    "$MINICONDA_DIR/condabin/conda" create --no-shortcuts -y -k --prefix "$ENV_DIR" python=3.10.12
    if [ $? -ne 0 ]; then
        echo "Failed to create conda environment"
        exit 1
    fi
    echo "Conda environment created successfully"
    echo

    if [ -f "$ENV_DIR/bin/python" ]; then
        echo "Installing specific pip version..."
        "$ENV_DIR/bin/python" -m pip install "pip==24.1.2"
        if [ $? -ne 0 ]; then
            echo "Failed to install pip"
            exit 1
        fi
        echo "Pip installation complete"
        echo
    fi
}

install_dependencies() {
    echo "Installing dependencies..."
    source "$MINICONDA_DIR/etc/profile.d/conda.sh"
    conda activate "$ENV_DIR" || exit 1
    pip install -r "$INSTALL_DIR/requirements.txt" || exit 1
    conda deactivate
    echo "Dependencies installation complete"
    echo
}

set -e

check_privileges
cleanup
install_miniconda
create_conda_env
install_dependencies

echo "UVR5 UI has been installed successfully!"
echo "To start UVR5 UI, please run 'run-UVR5-UI.sh'"

read -p "Press Enter to exit..."

chmod +x "$0"
