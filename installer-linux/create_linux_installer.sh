#!/usr/bin/bash

SCRIPT_PATH=$(dirname -- "${BASH_SOURCE[0]}")

INPUT_DIR=${SCRIPT_PATH}/program
LICENSE_FILE=${INPUT_DIR}/LICENSE
OUTPUT_FILE=$1
LABEL="Erriez MIDI SYSEX-IO"

echo "Creating Linux installer"
makeself --sha256 --license "${LICENSE_FILE}" "${INPUT_DIR}" "${OUTPUT_FILE}" "${LABEL}" ./install.sh

echo "Created installer:"
./"${OUTPUT_FILE}" --check
./"${OUTPUT_FILE}" --info
./"${OUTPUT_FILE}" --list
