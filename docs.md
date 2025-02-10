
# UVR5-UI Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Features](#features)
3. [Requirements](#requirements)
4. [Getting Started](#getting-started)
5. [Installation Instructions](#installation-instructions)
6. [Running UVR5-UI](#running-uvr5-ui)
7. [Updating UVR5-UI](#updating-uvr5-ui)
8. [Docker Instance Setup](#docker-instance-setup)
9. [Contributions](#contributions)
10. [TO-DO](#to-do)
11. [Credits](#credits)
12. [Feedback and Support](#feedback-and-support)

---

## Introduction
UVR5-UI is a user-friendly interface for the Ultimate Vocal Remover 5, designed to separate audio files into various stems using multiple models. Built on top of the `python-audio-separator`, it provides a Gradio UI for easier interaction, making it accessible to both novice and advanced users.

---

## Features
- **User-Friendly Interface**: An intuitive Gradio UI for easy navigation and operation.
- **Multiple Models Supported**: Includes VR Arch, MDX-NET, Demucs v4, MDX23C, Mel-Band Roformer, BS Roformer, Music Source Separation, and VIP models.
- **Video/Audio Separation**: Supports separation from URLs using `yt_dlp`, covering platforms like YouTube, SoundCloud, etc.
- **Batch Processing**: Enables processing multiple files at once for efficiency.
- **Multi-Language Support**: Available in several languages to cater to a global user base.
- **Cross-Platform Compatibility**: Runs on Windows, Linux, and through cloud services like Colab, Kaggle, and Hugging Face Spaces.
- **Integration with Cloud Services**: Direct links to run in Google Colab, Kaggle, and Lightning.ai.

---

## Requirements
### Hardware Requirements
- **NVIDIA GPU**: RTX 2000 series or higher for optimal performance.
- **Disk Space**: Minimum 10 GB, with more recommended for model storage.

> **Note**: Older GPUs and CPUs may significantly slow down processing. Consider using cloud services if local hardware is insufficient.

### Software Requirements
- **Git**: For cloning the repository.
- **FFmpeg**: Essential for audio processing. Install from [FFmpeg](https://ffmpeg.org/download.html) or use the provided script for Windows.
- **System PATH**: Ensure FFmpeg is added to the system PATH (especially for Windows).

#### Linux Users
Run the following command to install prerequisites:
```bash
sudo apt install ffmpeg git  # For Debian/Ubuntu
sudo pacman -S ffmpeg git    # For Arch Linux
sudo dnf install ffmpeg git  # For Fedora
```

---

## Installation Instructions
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Eddycrack864/UVR5-UI.git
   ```
2. **Run the Installer**:
   - **Windows**: Double-click `UVR5-UI-installer.bat` (do not run as administrator).
   - **Linux**: Run the script after granting execution permissions:
     ```bash
     chmod +x UVR5-UI-installer.sh && ./UVR5-UI-installer.sh
     ```

> **Tip**: Consider running the updater script before installation to ensure the latest version.

---

## Running UVR5-UI
1. **Windows**:
   - Double-click `run-UVR5-UI.bat` to launch the UI.
2. **Linux**:
   ```bash
   chmod +x run-UVR5-UI.sh && ./run-UVR5-UI.sh
   ```

---

## Updating UVR5-UI
To update, run the respective updater script:
- **Windows**: Double-click `UVR5-UI-updater.bat`.
- **Linux**: 
  ```bash
  chmod +x UVR5-UI-updater.sh && ./UVR5-UI-updater.sh
  ```

---

## Docker Instance Setup
For advanced users, a Docker setup is available:
1. **Prerequisites**:
   - Docker image based on Ubuntu 20.04 or higher.
   - At least 20 GB of storage.
   - Jupyter Notebook version 7.3.1 or newer.
   - Port forwarding configured for 9999.
   - GPU drivers installed for CUDA support.

2. **Jupyter Notebook**:
   - Access the notebook [here](https://github.com/Eddycrack864/UVR5-UI/blob/main/UVR_UI_Jupyter.ipynb) for setup instructions.

---

## Contributions
Contributions are welcome! Feel free to:
- Report issues or bugs via the [issue tracker](https://github.com/Eddycrack864/UVR5-UI/issues).
- Submit improvements through [pull requests](https://github.com/Eddycrack864/UVR5-UI/pulls).

Star the repository if you find it useful, and consider donating to support the project.

---

## TO-DO
- Expand language support.
- Integrate additional models for enhanced functionality.

---

## Credits
Special thanks to:
- [beveradb](https://github.com/beveradb) for `python-audio-separator`.
- [Ilaria](https://github.com/TheStingerX) for hosting on Hugging Face Spaces.
- [Mikus](https://github.com/cappuch) for code contributions.
- [Nick088](https://github.com/Nick088Official) for Roformer fixes.
- [yt_dlp](https://github.com/yt-dlp/yt-dlp) developers for their support.
- [Blane187](https://huggingface.co/Blane187) and [ArisDev](https://github.com/aris-py) for improvements and Kaggle integration.

---

## Feedback and Support
- **Troubleshooting**: Check the [troubleshooting guide](https://github.com/Eddycrack864/UVR5-UI/blob/main/info/troubleshooting.md).
- **Community**: Join the [AI HUB Discord](https://discord.gg/aihub) for support and discussions.
- **Issues**: Report any unresolved issues [here](https://github.com/Eddycrack864/UVR5-UI/issues).

