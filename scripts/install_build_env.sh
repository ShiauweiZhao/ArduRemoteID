#!/bin/bash
set -euo pipefail

VENV=${VENV:-.venv}
PYTHON=${PYTHON:-python3}
ARDUINO_CLI_VERSION=0.27.1
ARDUINO_CLI_ARCHIVE=arduino-cli_${ARDUINO_CLI_VERSION}_Linux_64bit.tar.gz

"${PYTHON}" -m venv "${VENV}"
"${VENV}/bin/python" -m pip install --upgrade pip
"${VENV}/bin/python" -m pip install \
    empy==3.3.4 \
    pymavlink \
    dronecan \
    pyserial \
    pexpect \
    pymonocypher==3.1.3.2

if [ ! -x bin/arduino-cli ]; then
    if [ ! -f "${ARDUINO_CLI_ARCHIVE}" ]; then
        rm -f "${ARDUINO_CLI_ARCHIVE}.tmp"
        wget -O "${ARDUINO_CLI_ARCHIVE}.tmp" "https://downloads.arduino.cc/arduino-cli/${ARDUINO_CLI_ARCHIVE}"
        mv "${ARDUINO_CLI_ARCHIVE}.tmp" "${ARDUINO_CLI_ARCHIVE}"
    fi
    mkdir -p bin
    tar xvzf "${ARDUINO_CLI_ARCHIVE}" -C bin
fi
