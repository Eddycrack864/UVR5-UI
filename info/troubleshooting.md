Here are some common errors that could happen during the installation or running process

## 1. UnicodeDecodeError: 'charmap' codec can't decode byte X in position Y: character maps to undefined

### What is this?

UVR5 UI has multi-language support so it needs UTF-8 Unicode encoding to run properly, even though all files have that encoding this error still occurs. If you know how to fix it I would appreciate it if you could make a pull request with the solution.

### How to solve it?

Follow the following steps:

1. Open the Control Panel
2. Click Clock, Language, and Region
3. Click Region
4. Click the Administrative tab
5. Under Language for non-Unicode programs, click Change system locale
6. Then check: Beta: Use Unicode UTF-8 for worldwide language support
7. I recommend restarting the PC

## 2. HF_HUB_DISABLE_SYMLINKS_WARNING

### What's this?

This message is actually a warning, not an error, telling you that on your setup (Windows + no dev mode) the user experience when caching files will be slightly degraded due to symlinks not been supported.

### How to solve it?

Follow the steps described [here](https://learn.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development)