#!/bin/bash
set -euo pipefail

# Versions shared by fresh installs and updates (UVR5-UI-updater.sh runs this script with --update)
MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py313_26.7.1-1-Linux-x86_64.sh"
PYTHON_VERSION="3.13.16"
PIP_VERSION="26.2.1"
TORCH_VERSION="2.7.1"
TORCHVISION_VERSION="0.22.1"
TORCH_INDEX="https://download.pytorch.org/whl/cu128"

INSTALL_DIR="$(pwd)"
MINICONDA_DIR="$HOME/miniconda3"
ENV_DIR="$INSTALL_DIR/env"
OLD_ENV_DIR="$INSTALL_DIR/env_old"
CONDA_EXE="$MINICONDA_DIR/bin/conda"
PYTHON_EXE="$ENV_DIR/bin/python"
UPDATE_MODE=0

pause_if_interactive() {
    if [ -t 0 ]; then
        read -r -p "Press Enter to exit..."
    fi
}

fail() {
    echo "ERROR: $1"
    # In update mode the updater pauses on failure
    [ "$UPDATE_MODE" = 1 ] || pause_if_interactive
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

# Some dependencies (diffq) have no prebuilt package for this Python on Linux and are compiled during install.
check_compiler() {
    if command -v gcc >/dev/null 2>&1; then
        return 0
    fi
    echo "A C compiler (gcc) is required to install UVR5 UI, but it was not found."
    echo "Install it with the command for your distribution and run this script again:"
    echo "  Debian/Ubuntu: sudo apt install build-essential"
    echo "  Arch Linux:    sudo pacman -S base-devel"
    echo "  Fedora:        sudo dnf install gcc gcc-c++"
    fail "gcc not found"
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

# Creates env/ from scratch: Python from conda-forge (no Anaconda Terms of Service prompt), torch, then requirements.
# Returns non-zero instead of exiting so a failed rebuild can be rolled back.
build_env() {
    echo "Creating Conda environment with Python $PYTHON_VERSION..."
    "$MINICONDA_DIR/condabin/conda" create --no-shortcuts -y -k --override-channels -c conda-forge \
        --prefix "$ENV_DIR" "python=$PYTHON_VERSION" || return 1
    [ -f "$PYTHON_EXE" ] || return 1
    echo "Conda environment created successfully"
    echo

    echo "Installing pip $PIP_VERSION..."
    "$PYTHON_EXE" -m pip install "pip==$PIP_VERSION" || return 1
    echo

    install_torch || return 1
    install_requirements || return 1
    verify_env || return 1
    echo "Dependencies installation complete"
    echo
}

install_torch() {
    echo "Installing torch $TORCH_VERSION..."
    "$PYTHON_EXE" -m pip install "torch==$TORCH_VERSION" "torchvision==$TORCHVISION_VERSION" --index-url "$TORCH_INDEX" \
        || return 1
    echo
}

install_requirements() {
    echo "Installing dependencies..."
    "$PYTHON_EXE" -m pip install --upgrade -r "$INSTALL_DIR/requirements.txt" || return 1
    echo
}

verify_env() {
    "$PYTHON_EXE" -c "import audio_separator.separator, gradio, torch" && return 0
    echo "The Python environment is incomplete: some dependencies could not be imported"
    return 1
}

# ---------------------------------------------------------------------------
# Update mode, called by UVR5-UI-updater.sh after the code has been updated.
# ---------------------------------------------------------------------------

restore_old_env() {
    rm -rf "$ENV_DIR"
    mv "$OLD_ENV_DIR" "$ENV_DIR" || fail "Could not restore '$OLD_ENV_DIR'. Rename it to 'env' manually."
    echo "Previous environment restored."
}

# env_old/ only exists if a rebuild was interrupted: keep env/ if it is complete, otherwise bring env_old/ back.
recover_interrupted_rebuild() {
    [ -d "$OLD_ENV_DIR" ] || return 0
    if [ -f "$PYTHON_EXE" ] && verify_env >/dev/null 2>&1; then
        rm -rf "$OLD_ENV_DIR"
        return 0
    fi
    echo "A previous environment rebuild was interrupted. Restoring your previous environment..."
    restore_old_env
}

env_is_outdated() {
    "$PYTHON_EXE" -c "import sys; sys.exit(sys.version_info[:2] >= tuple(map(int, sys.argv[1].split('.')[:2])))" \
        "$PYTHON_VERSION"
}

offer_rebuild() {
    echo
    echo "UVR5 UI now uses Python $PYTHON_VERSION, but your Python environment is older."
    echo "It can be rebuilt automatically: this downloads about 3 GB and needs about 6 GB of free disk space."
    echo "If anything goes wrong, your current environment is restored."
    echo
    local answer="n"
    if [ -t 0 ]; then
        read -r -p "Rebuild the Python environment now? [y/N] " answer
    fi
    if [[ ! "$answer" =~ ^[Yy] ]]; then
        echo
        echo "Skipping the rebuild. Updating the dependencies of your current environment..."
        install_requirements || fail "Failed to update dependencies."
        echo "You can rebuild the environment later by running the updater again."
        return 0
    fi

    check_compiler
    install_miniconda  # precompiled versions ship env/ without Miniconda
    rm -rf "$OLD_ENV_DIR"
    mv "$ENV_DIR" "$OLD_ENV_DIR" || fail "Could not move the current environment."

    if ! build_env; then
        echo
        echo "The rebuild failed. Restoring your previous environment..."
        restore_old_env
        fail "The Python environment could not be rebuilt. Check the output above for details."
    fi

    echo "Removing the previous environment..."
    rm -rf "$OLD_ENV_DIR"
    echo "Python environment rebuilt successfully."
}

update() {
    recover_interrupted_rebuild
    [ -f "$PYTHON_EXE" ] || fail "Python environment not found at '$ENV_DIR'. Please run the installer first."

    if env_is_outdated; then
        offer_rebuild
        return 0
    fi

    echo "Checking for updated dependencies..."
    install_torch || fail "Failed to update torch."
    install_requirements || fail "Failed to update dependencies."
    echo "Python environment updated successfully."
}

if [ "${1:-}" = "--update" ]; then
    UPDATE_MODE=1
    update
    exit 0
fi

echo -e "\e]2;UVR5 UI Installer\a"
echo "Welcome to the UVR5 UI Installer!"
echo

check_privileges
check_path
check_compiler
install_miniconda
build_env || fail "Failed to install UVR5 UI. Check the output above for details."

echo "UVR5 UI has been installed successfully!"
echo "To start UVR5 UI, please run 'run-UVR5-UI.sh'"
pause_if_interactive
