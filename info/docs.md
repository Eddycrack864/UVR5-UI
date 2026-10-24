# UVR5-UI Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Features](#features)
3. [Requirements](#requirements)
4. [Installation Instructions](#installation-instructions)
5. [Running UVR5-UI](#running-uvr5-ui)
6. [Updating UVR5-UI](#updating-uvr5-ui)
7. [Docker Instance Setup](#docker-instance-setup)
8. [Ensembles](#ensembles)
9. [Stem Mixer](#stem-mixer)
10. [Settings](#settings)
11. [Accessibility](#accessibility)
12. [Best Models](#best-models)
13. [Advanced Documentation](#advanced-documentation)
14. [Contributions](#contributions)
15. [TO-DO](#to-do)
16. [Credits](#credits)
17. [Feedback and Support](#feedback-and-support)

## Introduction
UVR5-UI is a user-friendly interface for the Ultimate Vocal Remover 5, designed to separate audio files into various stems using multiple models. Built on top of the `python-audio-separator`, it provides a Gradio UI for easier interaction, making it accessible to both novice and advanced users.

## Features
- **User-Friendly Interface**: An intuitive Gradio UI for easy navigation and operation.
- **Multiple Models Supported**: Includes VR Arch, MDX-NET, Demucs v4, MDX23C, Mel-Band Roformer, BS Roformer, Music Source Separation, and VIP models.
- **Video/Audio Separation**: Supports separation from URLs using `yt_dlp`, covering platforms like YouTube, SoundCloud, etc.
- **Batch Processing**: Enables processing multiple files at once for efficiency.
- **Ensembles**: Combines the results of several models, with curated presets and your own (see [Ensembles](#ensembles)).
- **Stem Mixer**: Plays all the stems together with a volume, mute and solo control per stem, and downloads the mix (see [Stem Mixer](#stem-mixer)).
- **Performance Settings**: Native FP16, torch.compile and chunked processing for long audio (see [Settings](#settings)).
- **Accessibility**: Usable with the keyboard and screen readers such as NVDA (see [Accessibility](#accessibility)).
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

Your preferences (language, theme, saved separation settings) are stored in `user_data/` and are kept across updates.

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

## Ensembles
The **Ensemble** tab runs two to six models (of any architecture) on the same audio and combines the stems they have in common into one result, which is usually cleaner than any single model.

- **Presets**: curated combinations from the [audio-separator](https://github.com/nomadkaraoke/python-audio-separator) community guide (Vocal Balanced/Clean/Full/RVC, Instrumental Clean/Full/Balanced/Low Resource, Karaoke). Choose one and its models, algorithm and weights are filled in. You can save your own combinations as presets (*Manage presets*); they are stored in `user_data/ensemble_presets.json`.
- **Model settings**: each model runs with the *Advanced settings* of its own architecture tab, so tune a Roformer model in the Roformer tab and it will be used like that in the ensemble.
- **Algorithms**:

| Algorithm | What it does | Weights |
|---|---|---|
| `avg_wave` / `avg_fft` | Weighted average of the waveforms / spectrograms. A safe default | Yes |
| `median_wave` / `median_fft` | Median: ignores the model that differs the most. Use 3+ models | No |
| `min_wave` / `min_fft` | Keeps the quietest result: less bleed, thinner sound (e.g. clean vocals) | No |
| `max_wave` / `max_fft` | Keeps the loudest result: fuller sound, more bleed (e.g. full vocals) | No |
| `uvr_max_spec` / `uvr_min_spec` | Max Spec / Min Spec from Ultimate Vocal Remover (popular for instrumentals) | No |
| `ensemble_wav` | UVR's chunk ensemble: keeps the least noisy chunk of every model. Experimental | No |

- Only the stems produced by **every** model are combined (e.g. Vocals and Instrumental). Enable *Include unmatched stems* to also get the rest, and *Keep each model's stems* to save each model's own output next to the result.
- Batches process the files model by model, so each model is loaded once per group of files.

## Stem Mixer
After a single-file separation that gives two or more stems, a **Stem mixer** section appears under the output players (in every architecture tab and in the Ensemble tab). Open it to listen to all the stems together, which makes it easy to check the separation: hear the rebuilt mix, find bleed between stems or compare how much of each stem is left.

- **Playback**: ▶ plays every stem at the same time, perfectly in sync. Use ■ to stop and the position bar to jump to any point.
- **Volume**: each stem has its own slider, from 0% to 150%, and the changes are heard right away while it plays.
- **M (Mute)** silences a stem. **S (Solo)** plays only the soloed stems (several can be soloed at once); solo wins over mute.
- **Download mix (.wav)**: saves the mix with the current volumes, mute and solo as `<song>_mix.wav`, at the stems' own sample rate. It is a 32-bit float WAV, so turning stems above 100% doesn't clip the file.

Notes:
- Everything runs in your browser: the stems are only loaded when you press ▶ or download the mix, and they take about 10 MB of browser memory per minute of audio per stem (a 5-minute song with 6 stems uses about 300 MB).
- A stem in a format that your browser can't play (AIFF or AC3 in some browsers) is marked in its row and left out; the rest still work. WAV, FLAC and MP3 work in every browser.
- Batch separations don't show the mixer: it uses the stems shown in the output players.

## Settings
- **Performance** (applies to every tab):
  - *Precision*: Automatic (autocast on NVIDIA GPUs), FP32, Autocast or Native FP16. Native FP16 makes BS/Mel Roformer models faster and lighter on NVIDIA and Apple GPUs; other combinations fall back to FP32.
  - *torch.compile*: speeds up long or repeated Roformer separations; the first one is slower. It needs Triton (Linux, Colab, Kaggle) and is skipped otherwise.
  - *Process long audio in chunks*: splits audio longer than the given seconds (e.g. 600 for files over an hour) to avoid running out of memory. Chunks are joined without a crossfade.
  - *Write outputs with soundfile*: uses less memory when writing very long files.
- **Output file names**: a template with `{input}`, `{stem}` and `{model}`, e.g. `{stem} - {input}`. The default is `{input}_({stem})_{model}`.

## Accessibility
UVR5 UI can be used with the keyboard and a screen reader. It has been tested with **NVDA** on Windows and Chrome; other screen readers (JAWS, Narrator, Orca, VoiceOver) should work as well, since it uses standard ARIA roles and live regions.

- **Tabs**: Tab moves into the tab bar and out of it in one step; use the **Left/Right arrows** (or Home/End) to move between tabs and **Enter** or **Space** to open one.
- **Model and format lists**: they are combo boxes. Press **Down arrow** to open the list and move through the models (e.g. "BS Roformer SW by jarredou (Vocals ⭐), 2 of 92"), or type part of a name to filter it, and press **Enter** to choose. The focus stays on the list. The recommended model of each stem is the first one, marked with a ⭐.
- **Advanced settings, Separation by link, Batch separation**: they are collapsible sections; screen readers say whether each one is expanded or collapsed. Press Enter on its title to open or close it.
- **What gets announced**:
  - validation messages, e.g. "Please select a model first";
  - when "All models" / "Downloaded models only" change the list ("Models in the list: 92");
  - the progress of a separation, and which stems it produced ("Separation finished: Vocals, Instrumental");
  - the summary of a batch separation;
  - errors and notifications.
- **Single file vs. batch**: the batch button is called "Separate all files!", so it isn't confused with "Separate!".
- **Stem mixer**: every control has a name ("Mute: Vocals", "Volume: Vocals"), and the volume sliders are read as a percentage.
- **Language**: the page uses the language selected in Settings, so screen readers can pick the matching voice. In NVDA this needs *Automatic language switching* enabled (Settings → Speech) and a voice for that language installed in Windows.
- **Keyboard focus** is always shown with a visible outline, with any theme.

Known limitations (they come from Gradio, the framework UVR5 UI is built on):
- NVDA says "clickable" on some paragraphs and regions.
- The "Reset to default value" buttons next to each slider don't say which setting they reset; the slider before them does.
- Descriptions under some checkboxes aren't read when the checkbox gets the focus.

If something isn't accessible to you, please [open an issue](https://github.com/Eddycrack864/UVR5-UI/issues) describing your screen reader, browser and what happened.

## Best Models
### Instrumental
1. BS Roformer | Instrumental Resurrection by unwa (Added)
2. MelBand Roformer Kim | Inst V1 (E) Plus by Unwa (Added)
3. MelBand Roformer | Instrumental FV8 by Gabox (Added)

### Vocals
1. BS Roformer SW by jarredou (Added)
2. MelBand Roformer Kim | FT 2 Bleedless by unwa (Added)
3. BS Roformer | Vocals Resurrection by unwa (Added)

### Karaoke
1. BS Roformer | Karaoke by anvuew (Added)
2. BS Roformer | Karaoke by frazer-becruily (Added)

### De-Reverb
1. MelBand Roformer | De-Reverb by anvuew (Added)
2. MelBand Roformer | De-Reverb Mono by anvuew (Added)
3. MelBand Roformer | De-Reverb-Echo Fused by Sucial (Added)

### Denoise
1. MelBand Roformer | Denoise-Debleed by Gabox (Added)
2. Mel-Roformer-Denoise-Aufr33 (Added)
3. UVR-DeNoise (Added)

## Advanced Documentation
You can review more advanced and detailed documentation about models, UVR5 and other stuff [here](https://docs.google.com/document/d/17fjNvJzj8ZGSer7c7OFe_CNfUKbAxEh_OBv94ZdRG5c/edit?usp=sharing)

## Contributions
Contributions are welcome! Feel free to:
- Report issues or bugs via the [issue tracker](https://github.com/Eddycrack864/UVR5-UI/issues).
- Submit improvements through [pull requests](https://github.com/Eddycrack864/UVR5-UI/pulls). See the [Development section of the README](https://github.com/Eddycrack864/UVR5-UI#development) for the project layout and how to run the tests.

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