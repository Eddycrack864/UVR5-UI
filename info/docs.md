# UVR5-UI Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Features](#features)
3. [Requirements](#requirements)
4. [Installation Instructions](#installation-instructions)
5. [Running UVR5-UI](#running-uvr5-ui)
6. [Updating UVR5-UI](#updating-uvr5-ui)
7. [Docker Instance Setup](#docker-instance-setup)
8. [Best Models](#best-models)
9. [Advanced Documentation](#advanced-documentation)
10. [Contributions](#contributions)
11. [TO-DO](#to-do)
12. [Credits](#credits)
13. [Feedback and Support](#feedback-and-support)

## Introduction
UVR5-UI is a user-friendly interface for the Ultimate Vocal Remover 5, designed to separate audio files into various stems using multiple models. Built on top of the `python-audio-separator`, it provides a Gradio UI for easier interaction, making it accessible to both novice and advanced users.

## Features
- **User-Friendly Interface**: An intuitive Gradio UI for easy navigation and operation.
- **Multiple Models Supported**: Includes VR Arch, MDX-NET, Demucs v4, MDX23C, Mel-Band Roformer, BS Roformer, Music Source Separation, and VIP models.
- **Video/Audio Separation**: Supports separation from URLs using `yt_dlp`, covering platforms like YouTube, SoundCloud, etc.
- **Batch Processing**: Enables processing multiple files at once for efficiency.
- **Multi-Language Support**: Available in several languages to cater to a global user base.
- **Cross-Platform Compatibility**: Runs on Windows, Linux, and through cloud services like Colab, Kaggle, and Hugging Face Spaces.
- **Integration with Cloud Services**: Direct links to run in Google Colab, Kaggle, and Lightning.ai.

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

## Installation Instructions
### Normal Installation
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

## Running UVR5-UI
1. **Windows**:
   - Double-click `run-UVR5-UI.bat` to launch the UI.
2. **Linux**:
   ```bash
   chmod +x run-UVR5-UI.sh && ./run-UVR5-UI.sh
   ```

## Updating UVR5-UI
To update, run the respective updater script:
- **Windows**: Double-click `UVR5-UI-updater.bat`.
- **Linux**: 
  ```bash
  chmod +x UVR5-UI-updater.sh && ./UVR5-UI-updater.sh
  ```

### Precompiled Version
1. Get the precompiled version (.zip) for your PC:
   - **[Windows](https://huggingface.co/Eddycrack864/UVR5-UI/tree/main/Windows)**
   - **[Linux](https://huggingface.co/Eddycrack864/UVR5-UI/tree/main/Linux)**

2. Extract the .zip file, I recommend using the "extract here" option.
3. You can now use all the features of the normal installation.

> **Note**: Still, to update UVR5 UI you need to install Git.

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

## Best Models
### Instrumental
1. BS Roformer | Instrumental Resurrection by unwa (Added)
2. MelBand Roformer Kim | Inst V1 (E) Plus by Unwa (Added)
3. MelBand Roformer | Instrumental Fullness V4 by Gabox (Pending)
4. MelBand Roformer | Instrumental FV8b by Gabox (Pending)
5. MelBand Roformer | INSTV7 by Gabox (Added)

### Vocals
1. MelBand Roformer 2025.07 (Only available on MVSEP)
2. MelBand Roformer Bas Curtiz edition (Only available on MVSEP)
3. MelBand Roformer Kim | FT2 Bleedlees by unwa (Added)
4. BS Roformer | Vocals Resurrection by unwa (Added)
5. BS Roformer | Vocals Revive V2 by Unwa (Added)

### Karaoke
1. BS Roformer | Karaoke by becruily-frazer (Pending)
2. MelBand Roformer Karaoke Fusion by Gonzaluigi (Pending)
3. MelBand Roformer | Karaoke by becruily (Added)
4. Mel-Roformer-Karaoke-Aufr33-Viperx (Added)

### De-Reverb
1. MelBand Roformer | De-Reverb by anvuew (Added)
2. BS Roformer | De-Reverb Room by anvuew (Pending)
3. MelBand Roformer | De-Reverb Mono by anvuew (Added)
4. MelBand Roformer | De-Reverb-Echo Fused by Sucial (Added)

### Denoise
1. Mel-Roformer-Denoise-Aufr33 (Added)
2. MelBand Roformer | Denoise-Debleed by Gabox (Added)
3. UVR-DeNoise (Added)

### Crowd
1. UVR-MDX-NET_Crowd_HQ_1 (Added)
2. Mel-Roformer-Crowd-Aufr33-Viperx (Added)

## Advanced Documentation
You can review more advanced and detailed documentation about models, UVR5 and other stuff [here](https://docs.google.com/document/d/17fjNvJzj8ZGSer7c7OFe_CNfUKbAxEh_OBv94ZdRG5c/edit?usp=sharing)

## Contributions
Contributions are welcome! Feel free to:
- Report issues or bugs via the [issue tracker](https://github.com/Eddycrack864/UVR5-UI/issues).
- Submit improvements through [pull requests](https://github.com/Eddycrack864/UVR5-UI/pulls).

Star the repository if you find it useful, and consider donating to support the project.

## TO-DO
- Expand language support.
- Integrate additional models for enhanced functionality.

## Credits
Special thanks to:
- [beveradb](https://github.com/beveradb) for `python-audio-separator`.
- [Ilaria](https://github.com/TheStingerX) for hosting on Hugging Face Spaces.
- [Mikus](https://github.com/cappuch) for code contributions.
- [Nick088](https://github.com/Nick088Official) for Roformer fixes.
- [yt_dlp](https://github.com/yt-dlp/yt-dlp) developers for their support.
- [Blane187](https://huggingface.co/Blane187) and [ArisDev](https://github.com/aris-py) for improvements and Kaggle integration.

## Feedback and Support
- **Troubleshooting**: Check the [troubleshooting guide](https://github.com/Eddycrack864/UVR5-UI/blob/main/info/troubleshooting.md).
- **Community**: Join the [AI HUB Discord](https://discord.gg/aihub) for support and discussions.
- **Issues**: Report any unresolved issues [here](https://github.com/Eddycrack864/UVR5-UI/issues).