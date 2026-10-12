Here are some common errors that could happen during the installation or running process

## 1. HF_HUB_DISABLE_SYMLINKS_WARNING

### What's this?

This message is actually a warning, not an error, telling you that on your setup (Windows + no dev mode) the user experience when caching files will be slightly degraded due to symlinks not been supported.

### How to solve it?

Follow the steps described [here](https://learn.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development)

## 2. No module named 'xxxxxx'

### What's this?

This indicates that the dependencies were not installed correctly or the script cannot find them.

### How to solve it?

- Make sure you installed UVR5 UI in a folder that does not require administrator permissions.
- Make sure the installation path does not have any special characters on it.
- If you installed UVR5 UI by downloading the .zip from `releases` make sure you rename it from `UVR5-UI-X.X.X` to just `UVR5-UI`

## 3. How to disable Discord Rich Presence?

1. Open UVR5 UI and go to the `Settings` tab
2. Open the `Discord Rich Presence` section and uncheck `Show UVR5 UI activity on Discord`
3. Restart UVR5 UI

The setting is saved in `user_data/config.json` (`"discord_presence": false`). Older versions kept it in `assets/config.json`, which is no longer used.

## 4. Failed building wheel for diffq (Linux)

### What's this?

On Linux one of the dependencies (`diffq`) has no prebuilt package for Python 3.13, so it is compiled during the installation. This error means no C compiler was found.

### How to solve it?

Install a compiler and run the installer or updater again: (Debian and Ubuntu users): `sudo apt install build-essential` (For Arch linux users): `sudo pacman -S base-devel` (For Fedora users): `sudo dnf install gcc gcc-c++`

## 5. The Python environment rebuild failed

### What's this?

When an installation still uses Python 3.10, the updater offers to rebuild the Python environment with Python 3.13. If the rebuild fails (no internet, not enough disk space, UVR5 UI was open...) your previous environment is restored, so UVR5 UI keeps working as before.

### How to solve it?

- Close UVR5 UI before running the updater.
- Make sure you have about 6 GB of free disk space and a stable internet connection.
- Run the updater again and accept the rebuild.
- If an `env_old` folder is left behind and `env` is missing, rename `env_old` to `env`.
