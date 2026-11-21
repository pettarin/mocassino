#!/bin/bash
#
# This file is part of the mocassino project
#
# To print the usage message, run: bash install.sh --help
#
set -euo pipefail

# Name of the service
SERVICE_NAME="mocassino"

# Name of the PyPI package
PYPI_NAME="$SERVICE_NAME"

# Library directory on target
LIBRARY_DIRECTORY_PATH="/music"

# ###########################################################################
# DO NOT MODIFY BELOW THIS LINE!
# ###########################################################################

# Script and project directory absolute paths
SCRIPT_DIRECTORY_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIRECTORY_PATH="$SCRIPT_DIRECTORY_PATH"

# File and directory names
VENV_NAME="venv"
EXECUTABLE_FILE_NAME="mocassino"
SERVICE_SYSTEMD_UNIT_FILE_NAME="$SERVICE_NAME.service"

# Absolute paths
INSTALLATION_DIRECTORY_PATH="/opt/$SERVICE_NAME"
RUN_DIRECTORY_PATH="$INSTALLATION_DIRECTORY_PATH/run"
CONFIG_DIRECTORY_PATH="$RUN_DIRECTORY_PATH/.config"
VENV_DIRECTORY_PATH="$INSTALLATION_DIRECTORY_PATH/$VENV_NAME"
EXECUTABLE_FILE_PATH="$VENV_DIRECTORY_PATH/bin/$EXECUTABLE_FILE_NAME"
SERVICE_SYSTEMD_UNIT_DESTINATION_FILE_PATH="/lib/systemd/system/$SERVICE_SYSTEMD_UNIT_FILE_NAME"

# Script logic starts here
INSTALL_SYSTEMD=1
INSTALL_VENV=1
RUN_ARGUMENTS="run"
UNINSTALL=1
UNINSTALL_ONLY=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-install-systemd)
            INSTALL_SYSTEMD=0
            shift
            ;;
        --no-install-venv)
            INSTALL_VENV=0
            shift
            ;;
        --no-uninstall-first)
            UNINSTALL=0
            shift
            ;;
        --run-arguments)
            RUN_ARGUMENTS="$2"
            shift 2
            ;;
        --uninstall)
            UNINSTALL=1
            UNINSTALL_ONLY=1
            shift
            ;;
        -h|--help)
            echo "Usage: bash $0 [options]"
            echo ""
            echo "Options:"
            echo "  --no-install-systemd            Do not install the systemd service"
            echo "  --no-install-venv               Do not install the virtual environment"
            echo "  --no-uninstall-first            Do not remove a previous installation before installing"
            echo "  --run-arguments STRING          Use the provided STRING as argument to the ExecStart command line of the systemd service (default: '$RUN_ARGUMENTS')"
            echo "  --uninstall                     Remove a previous installation and exit"
            echo ""
            echo "Note: this script must be executed as root, for instance with sudo"
            exit 0
            ;;
        *)
            echo "[ERRO] Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check root
if [[ $EUID -ne 0 ]]; then
    echo "[ERRO] This script must be executed as root, for instance with sudo."
    exit 2
fi

echo "[INFO] Running as:      '$EUID' (root)"
echo "[INFO] Run arguments:   '$RUN_ARGUMENTS'"
echo "[INFO] Opt directory:   '$OPT_DIRECTORY_PATH'"
echo "[INFO] Venv directory:  '$VENV_DIRECTORY_PATH'"

# Uninstall
if [[ $UNINSTALL -eq 1 ]]; then
    echo "[INFO] Uninstalling service $SERVICE_NAME ..."

    # stop, disable and remove systemd unit file
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "$SERVICE_SYSTEMD_UNIT_DESTINATION_FILE_PATH"
    systemctl daemon-reload
    echo "[INFO] Uninstalled $SERVICE_SYSTEMD_UNIT_DESTINATION_FILE_PATH"

    # remove the venv directory
    rm -rf "$VENV_DIRECTORY_PATH"
    echo "[INFO] Removed $VENV_DIRECTORY_PATH"

    # remove the installation directory
    rm -rf "$INSTALLATION_DIRECTORY_PATH"
    echo "[INFO] Removed $INSTALLATION_DIRECTORY_PATH"

    echo "[INFO] Uninstalling service $SERVICE_NAME ... done"

    if [[ $UNINSTALL_ONLY -eq 1 ]]; then
        echo "[INFO] Option --uninstall specified: exit without installing service $SERVICE_NAME"
        exit 0
    fi
fi

# Install the venv
if [[ $INSTALL_VENV -eq 1 ]]; then
    echo "[INFO] Installing venv ..."

    mkdir -p "$INSTALLATION_DIRECTORY_PATH"
    mkdir -p "$CONFIG_DIRECTORY_PATH"

    cd "$INSTALLATION_DIRECTORY_PATH"
    python3 -m venv "$VENV_NAME"
    source "$VENV_DIRECTORY_PATH/bin/activate"
    pip install "$PYPI_PACKAGE_NAME"

    # print version to prove installation was successful
    $EXECUTABLE_FILE_PATH --version

    # write the configuration
    $EXECUTABLE_FILE_PATH configuration -l "$LIBRARY_DIRECTORY_PATH" --defaults --orientation 180 -o -y

    deactivate
    echo "[INFO] Installing venv ... done"
fi

# Install the systemd service
if [[ $INSTALL_SYSTEMD -eq 1 ]]; then
    echo "[INFO] Installing systemd service ..."

    D="$SERVICE_SYSTEMD_UNIT_DESTINATION_FILE_PATH"

    echo "# This file is part of the mocassino project" > "$D"
    echo "" >> "$D"
    echo "[Unit]" >> "$D"
    echo "Description=Lightweight audio player based on MOC for Raspberry Pi Zero 2 devices with Pimoroni Pirate Audio hats" >> "$D"
    echo "Documentation=https://github.com/pettarin/mocassino" >> "$D"
    echo "After=sound.target" >> "$D"
    echo "" >> "$D"
    echo "[Service]" >> "$D"
    echo "Type=simple" >> "$D"
    echo "# assume mocassino is installed in $VENV_NAME," >> "$D"
    echo "# and $RUN_DIRECTORY_PATH exists (acting as the $HOME for the service)" >> "$D"
    echo "Environment=LG_WD=$RUN_DIRECTORY_PATH" >> "$D"
    echo "Environment=HOME=$RUN_DIRECTORY_PATH" >> "$D"
    echo "Environment=XDG_CONFIG_HOME=$CONFIG_DIRECTORY_PATH" >> "$D"
    echo "WorkingDirectory=$RUN_DIRECTORY_PATH" >> "$D"
    echo "ReadWritePaths=$RUN_DIRECTORY_PATH" >> "$D"
    echo "ExecStart=$EXECUTABLE_FILE_PATH $RUN_ARGUMENTS" >> "$D"
    echo "Restart=on-failure" >> "$D"
    echo "RestartSec=5" >> "$D"
    echo "" >> "$D"
    echo "# Security hardening" >> "$D"
    echo "NoNewPrivileges=yes" >> "$D"
    echo "ProtectHome=yes" >> "$D"
    echo "ProtectSystem=strict" >> "$D"
    echo "PrivateTmp=yes" >> "$D"
    echo "" >> "$D"
    echo "[Install]" >> "$D"
    echo "WantedBy=default.target" >> "$D"

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    systemctl restart "$SERVICE_NAME"
    echo "[INFO] Installing systemd service ... done"
fi

echo "[INFO] Installation of $SERVICE_NAME complete"
exit 0

