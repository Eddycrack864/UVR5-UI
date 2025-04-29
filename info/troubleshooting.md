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

1. Go to the `assets` folder and open `config.json`
2. On line 10, change the state of `discord_presence` from `true` to `false`
3. Save changes and restart UVR5 UI