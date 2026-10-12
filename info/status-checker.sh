#!/bin/bash

echo "UVR5 UI Status"
echo

cd "$(dirname "$0")"

if [ -x "../env/bin/audio-separator" ]; then
    ../env/bin/audio-separator -e
else
    echo "Searching for a global audio-separator installation..."
    if command -v audio-separator &> /dev/null; then
        audio-separator -e
    else
        echo "Error: audio-separator not found. Run 'UVR5-UI-installer.sh' first."
    fi
fi
