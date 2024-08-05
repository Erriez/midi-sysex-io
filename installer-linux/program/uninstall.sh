#!/usr/bin/bash

APP_EXE=erriez-midi-sysex-io
APP_ICO=pyside6.ico
APP_SHORTCUT=${APP_EXE}.desktop
APP_DEVELOPER=erriez

EXE_PATH=$HOME/.local/bin/${APP_DEVELOPER}
ICON_PATH=$HOME/.local/share/icons
SHORTCUT_PATH=$HOME/.local/share/applications

DST_ICON_FILE=${ICON_PATH}/${APP_ICO}
DST_SHORTCUT_FILE=${SHORTCUT_PATH}/${APP_SHORTCUT}

# Remove files and directories
rm -r "${EXE_PATH}"
rm "${DST_ICON_FILE}"
rm "${DST_SHORTCUT_FILE}"

echo "Uninstall completed"
