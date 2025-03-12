#!/bin/bash

echo "UVR5 UI Status"
echo

cd "$(dirname "$0")"

if [ -f "../env/bin/python" ]; then
    ../env/bin/python ../env/bin/audio-separator -e
else
    echo "Searching for global python..."
    if command -v python &> /dev/null; then
        python ../env/bin/audio-separator -e
    else
        echo "Error: Python not found."
    fi
fi