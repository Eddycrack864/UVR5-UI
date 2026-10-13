<h1 align="center"><b> 🎵 UVR5 UI 🎵 </b></h1>
<div align="center">

[![madewithlove](https://img.shields.io/badge/made_with-%E2%9D%A4-red?style=for-the-badge&labelColor=orange)](https://github.com/Eddycrack864/UVR5-UI)

![cutecounter](https://count.nett.moe/get/uvr5_ui_colab/img?theme=rule34)

[![Open In Colab](https://img.shields.io/badge/Colab-F9AB00?style=for-the-badge&logo=googlecolab&color=525252)](https://colab.research.google.com/github/Eddycrack864/UVR5-UI/blob/main/UVR_UI.ipynb)
[![Open In Kaggle](https://img.shields.io/badge/Kaggle-20BEFF?style=for-the-badge&logo=Kaggle&logoColor=white)](https://www.kaggle.com/code/eddycrack864/uvr5-ui)
<a target="_blank" href="https://lightning.ai/new?repo_url=https%3A%2F%2Fgithub.com%2FEddycrack864%2FUVR5-UI%2Fblob%2Fmain%2FUVR_UI.ipynb">
<img src="https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/studio-badge.svg" alt="Open in Studio"/></a>
[![Licence](https://img.shields.io/badge/LICENSE-MIT-green.svg?style=for-the-badge)](https://github.com/Eddycrack864/UVR5-UI/blob/main/LICENSE)
[![Discord](https://img.shields.io/badge/Community-Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/aihub)

This project is based on [python-audio-separator](https://github.com/karaokenerds/python-audio-separator) (a CLI version of UVR5). This project was originally created for the [AI ​​HUB](https://discord.gg/aihub) community.

</div>
<div align="center">
  
[![Hugging Face](https://huggingface.co/datasets/huggingface/badges/resolve/main/open-in-hf-spaces-xl-dark.svg?download=true)](https://huggingface.co/spaces/TheStinger/UVR5_UI)

You can also try it on HuggingFace Spaces running with Zero GPU (A100)!

</div>
 
<div align="center">

**[Docs](https://github.com/Eddycrack864/UVR5-UI/blob/main/info/docs.md) / [Troubleshooting](https://github.com/Eddycrack864/UVR5-UI/blob/main/info/troubleshooting.md)**

</div>

## Features: 
* User Friendly Interface
* All VR Arch Models
* All MDX-NET Models
* Demucs v4 Models
* MDX23C Models
* Mel-Band Roformer Models
* BS Roformer Models
* Music Source Separation Models
* VIP Models
* Separation of an audio/video from all sites supported by [yt_dlp](https://github.com/yt-dlp/yt-dlp). Check the complete list [here](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).
* Batch Separation
* Ensembles: combine 2 to 6 models of any architecture with 11 algorithms, curated presets or your own
* Native FP16, torch.compile and chunked processing for long audio (Settings > Performance)
* Custom output file names and a one-click download of all the stems
* Available in multiple languages
* Colab/Kaggle/Lightning.ai support
* Windows/Linux support

## Requirements

### Hardware Requirements:
* Nvidia Series 2000 (RTX) or higher.
* At least 10Gb of disk space. 

> [!NOTE]  
> Older NVIDIA GPUs will be very slow. CPU will be insanely slow. If you don't meet the hardware requirements use our [Colab](https://colab.research.google.com/github/Eddycrack864/UVR5-UI/blob/main/UVR_UI.ipynb)/[Kaggle](https://www.kaggle.com/code/eddycrack864/uvr5-ui)/[Lightning.ai](https://lightning.ai/eddycrack864/studios/uvr5-ui)/[Hugging Face](https://huggingface.co/spaces/TheStinger/UVR5_UI).

### Prerequisites:
- Git. You can download Git [here](https://git-scm.com/downloads).
- FFmpeg. You can download FFmpeg [here](https://www.ffmpeg.org/download.html) or you can use my [automated installation script](https://github.com/Eddycrack864/UVR5-UI/blob/main/info/ffmpeg-installer.bat) (for Windows).
- For linux users, run this command on an terminal: (Debian and Ubuntu users): `sudo apt install ffmpeg git build-essential` (For Arch linux users): `sudo pacman -S ffmpeg git base-devel` (For Fedora users): `sudo dnf install ffmpeg git gcc gcc-c++`
(Some distributions already come with Git, FFmpeg and a C compiler preinstalled so this step may be optional. The compiler is needed to build one of the dependencies during installation.)

> [!IMPORTANT]  
> FFmpeg has to be added to the PATH. (only needed on Windows)

## Getting Started

Clone the repository (git needed) or download the source code of the latest release [here](https://github.com/Eddycrack864/UVR5-UI/releases)

```
git clone https://github.com/Eddycrack864/UVR5-UI.git
```

Then continue with the steps described below

### 1. Installation

Run the installation script based on your operating system:

- **Windows:** Double-click `UVR5-UI-installer.bat` (DONT RUN AS ADMINISTRATOR 🚧).
- **Linux:** Run `UVR5-UI-installer.sh` with `chmod +x UVR5-UI-installer.sh` and `./UVR5-UI-installer.sh`.

### 2. Running UVR5 UI

Start UVR5 UI using:

- **Windows:** Double-click `run-UVR5-UI.bat`.
- **Linux:** Run `run-UVR5-UI.sh` with `chmod +x run-UVR5-UI.sh` and `./run-UVR5-UI.sh`.

Extra options can be added to the run scripts (or to `python app.py`):

| Option | Description |
|---|---|
| `--share` | Create a temporary public Gradio link |
| `--listen-port 8080` | Use another port (default: 9999) |
| `--server-name 0.0.0.0` | Make the UI reachable from other devices on your network |
| `--open` | Open the UI in your browser (the run scripts already do this) |
| `--run-history` | Keep a history of your separations in the browser (off by default) |

Example: `run-UVR5-UI.bat --share --listen-port 8080`

### 3. Update UVR5 UI (If you want/need it)

Update UVR5 UI using (git needed):

- **Windows:** Double-click `UVR5-UI-updater.bat`.
- **Linux:** Run `UVR5-UI-updater.sh` with `chmod +x UVR5-UI-updater.sh` and `./UVR5-UI-updater.sh`.

Your preferences (language, theme, saved separation settings) live in the `user_data/` folder and your models in `models/`; updating never touches them.

UVR5 UI runs on Python 3.13. If your installation is older (Python 3.10), the updater offers to rebuild the Python environment automatically. It downloads about 3 GB and needs about 6 GB of free disk space while it runs; if anything fails, your previous environment is restored.

If you find an error when installing or running the program please consult [this troubleshooting file](https://github.com/Eddycrack864/UVR5-UI/blob/main/info/troubleshooting.md) first, if your error is not described there please create an [issue](https://github.com/Eddycrack864/UVR5-UI/issues)

### 4. Debug (If you want/need it)

Check the status of audio-separator core:

- **Windows:** Double-click `info/status-checker.bat`.
- **Linux:** Run `info/status-checker.sh` with `chmod +x info/status-checker.sh` and `./info/status-checker.sh`.

## Development

The app is a Python package, `uvr5_ui/`, organised in layers:

| Path | What lives there |
|---|---|
| `app.py` | Thin launcher (`python app.py [options]`, or `python -m uvr5_ui`) |
| `uvr5_ui/core/` | Separation, model catalog, downloads, leaderboard. No Gradio imports, testable on its own |
| `uvr5_ui/core/separation/specs.py` | One declarative `ArchSpec` per architecture (parameters, ranges, defaults). All separation tabs and the separation service are generated from it |
| `uvr5_ui/ui/` | Gradio layer: one module per tab in `ui/tabs/`, plus shared widgets and handler adapters |
| `uvr5_ui/config/` | App config (`assets/config.default.json` merged with `user_data/config.json`) and separation presets |
| `assets/` | Data only: model catalog (`models.json`), default settings, translations, themes |

Common tasks:

```bash
# Install the test tools (once) and run the tests
env/python.exe -m pip install -r requirements-dev.txt   # Linux: env/bin/python
env/python.exe -m pytest

# Check that every translatable string exists in assets/i18n/languages/en_US.json
env/python.exe tools/i18n_scan.py --check
```

- **Add a model:** add an entry to `assets/models.json` (`id`, `arch`, `filename`, download `sources`). It appears in its tab automatically.
- **Add a parameter:** add a `ParamSpec` to its architecture in `uvr5_ui/core/separation/specs.py` and its default to `assets/default_settings.json`.
- **Translations:** the English text passed to `i18n("...")` is the key in every language file, so changing it breaks existing translations.

## Precompiled Version
1. Get the precompiled version (.zip) for your PC:
   - **[Windows](https://huggingface.co/Eddycrack864/UVR5-UI/tree/main/Windows)**
   - **[Linux](https://huggingface.co/Eddycrack864/UVR5-UI/tree/main/Linux)**

2. Extract the .zip file, I recommend using the "extract here" option.
3. You can now use all the features of the normal installation.

> [!NOTE]  
> Still, to update UVR5 UI you need to install Git.

There is also a pre-compiled version primarily for Chinese users developed by jian27, get it [here](https://www.jian27.com/html/2231.html). Just 2.6 GB! 

## Docker Instance

A more technical level is required for this type of use. You can use this Jupyter notebook to initialize UVR5 on virtual machines with GPU. This will install the entire UVR5 from the main branch of GitHub.

### Requirements/Recommendations
- Use the docker image `>= ubuntu/ubuntu:20.04`
- At least `20 GB of storage minimum.` (Add more space for your models/training)
- Use Jupyter `>= 7.3.1`
- Configure port forwarding `9999 (UVR5-UI GUI)`
- Install necessary drivers to use the GPU
- Install a C compiler (`apt install build-essential`), needed to build one of the dependencies

You can get the notebook here: [Jupyter Notebook](https://github.com/Eddycrack864/UVR5-UI/blob/main/UVR_UI_Jupyter.ipynb) by iroaK


## Contributions
If you want to participate and help me with this project feel free to create an [issue](https://github.com/Eddycrack864/UVR5-UI/issues) if something goes wrong or make a [pull request](https://github.com/Eddycrack864/UVR5-UI/pulls) to improve this project.

Any type of contribution is welcome 💖

If you like this project you can star this repository. I will appreciate a lot 💖💖💖

You can donate to the original UVR5 project here:

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/uvr5)

## TO-DO
* Add more models
* Add more output formats

## Credits
* python-audio-separator by [beveradb](https://github.com/beveradb).
* Special thanks to [Ilaria](https://github.com/TheStingerX) for hosting this space and help 💖
* Thanks to [Mikus](https://github.com/cappuch) for the help with the code.
* Thanks to [Nick088](https://github.com/Nick088Official) for the help to fix roformers.
* Thanks to [yt_dlp](https://github.com/yt-dlp/yt-dlp) devs.
* Separation by link source code and improvements by [NeoDev](https://github.com/TheNeodev).
* Thanks to [ArisDev](https://github.com/aris-py) for porting UVR5 UI to Kaggle and improvements.