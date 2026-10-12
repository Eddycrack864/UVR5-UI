#!/bin/bash
set -euo pipefail

INSTALL_DIR="$(pwd)"
MINICONDA_DIR="$HOME/miniconda3"
ENV_DIR="$INSTALL_DIR/env"
MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py310_24.9.2-0-Linux-x86_64.sh"
CONDA_EXE="$MINICONDA_DIR/bin/conda"

echo -e "\e]2;UVR5 UI Installer\a"
echo "Welcome to the UVR5 UI Installer!"
echo

pause_if_interactive() {
    if [ -t 0 ]; then
        read -r -p "Press Enter to exit..."
    fi
}

fail() {
    echo "ERROR: $1"
    pause_if_interactive
    exit 1
}

check_privileges() {
    if [ "$(id -u)" -eq 0 ]; then
        fail "This script must not be run with sudo/root privileges. Please run it as a normal user without sudo"
    fi
    echo "The script is running without root privileges, continuing..."
    echo
}

check_path() {
    if [[ "$INSTALL_DIR" =~ [[:space:]] ]]; then
        echo "WARNING: The installation path contains spaces: $INSTALL_DIR"
        echo "Conda environments in paths with spaces or special characters often fail to install."
        echo
    fi
}

download() {
    local url="$1" output="$2"
    if command -v wget >/dev/null 2>&1; then
        wget "$url" -O "$output"
    elif command -v curl >/dev/null 2>&1; then
        curl -L "$url" -o "$output"
    else
        fail "Neither wget nor curl is installed"
    fi
}

install_miniconda() {
    if [ -f "$CONDA_EXE" ]; then
        echo "Miniconda already installed. Skipping installation..."
        return 0
    fi

    echo "Miniconda not found. Starting download and installation..."
    download "$MINICONDA_URL" miniconda.sh || fail "Download failed. Please check your internet connection and try again"
    bash miniconda.sh -b -p "$MINICONDA_DIR" || fail "Miniconda installation failed"
    rm miniconda.sh
    echo "Miniconda installation complete"
    echo
}

create_conda_env() {
    echo "Creating Conda environment..."
    "$MINICONDA_DIR/condabin/conda" create --no-shortcuts -y -k --prefix "$ENV_DIR" python=3.10.12 \
        || fail "Failed to create conda environment"
    echo "Conda environment created successfully"
    echo

    if [ -f "$ENV_DIR/bin/python" ]; then
        echo "Installing specific pip version..."
        "$ENV_DIR/bin/python" -m pip install "pip==24.1.2" || fail "Failed to install pip"
        echo "Pip installation complete"
        echo
    fi
}

install_dependencies() {
    echo "Installing dependencies..."
    # conda's activation scripts reference unset variables
    set +u
    source "$MINICONDA_DIR/etc/profile.d/conda.sh"
    conda activate "$ENV_DIR" || fail "Failed to activate the conda environment"
    set -u
    pip install -r "$INSTALL_DIR/requirements.txt" || fail "Failed to install requirements"
    pip uninstall torch torchvision -y || fail "Failed to uninstall torch"
    pip install torch==2.7.0 torchvision --upgrade --index-url https://download.pytorch.org/whl/cu128 \
        || fail "Failed to install torch"
    set +u
    conda deactivate
    set -u
    echo "Dependencies installation complete"
    echo
}

check_privileges
check_path
install_miniconda
create_conda_env
install_dependencies

echo "UVR5 UI has been installed successfully!"
echo "To start UVR5 UI, please run 'run-UVR5-UI.sh'"
pause_if_interactive
