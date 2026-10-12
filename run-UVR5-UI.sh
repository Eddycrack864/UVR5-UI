#!/bin/bash

echo -e "\e]2;UVR5 UI\a"
cd "$(dirname "$0")"

# Extra arguments are passed through, e.g.: ./run-UVR5-UI.sh --share --listen-port 8080
if [ -x "env/bin/python" ]; then
    PYTHON="env/bin/python"
else
    echo "Searching for global python and dependencies..."
    if command -v python3 &> /dev/null; then
        PYTHON="python3"
    elif command -v python &> /dev/null; then
        PYTHON="python"
    else
        echo "Error: Python not found. Please install UVR5 UI globally or run 'UVR5-UI-installer.sh' to set up the environment."
        [ -t 0 ] && read -r -p "Press Enter to exit..."
        exit 1
    fi
fi

"$PYTHON" app.py --open "$@"
status=$?

if [ $status -ne 0 ]; then
    echo
    echo "UVR5 UI exited with an error. Check the output above for details."
    [ -t 0 ] && read -r -p "Press Enter to exit..."
fi
exit $status
