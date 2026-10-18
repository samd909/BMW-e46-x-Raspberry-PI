
#!/usr/bin/env bash
set -euo pipefail

RULES="/etc/udev/rules.d/99-bmw-serial.rules"

if [[ $EUID -ne 0 ]]; then
    echo "Run this script with sudo:"
    echo "  sudo bash $0"
    exit 1
fi

if ! command -v udevadm >/dev/null 2>&1; then
    echo "Error: udevadm is not installed."
    exit 1
fi

echo "Creating persistent BMW serial device names..."

cat > "$RULES" <<'EOF'
# ModBMW iBus adapter - CP2102
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", ATTRS{serial}=="0001", SYMLINK+="bmw-ibus"

# BMW OBD2 FT232 cable
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="A6000001", SYMLINK+="bmw-obd"
EOF

udevadm control --reload-rules
udevadm trigger --subsystem-match=tty

echo
echo "Rules installed: $RULES"
echo
echo "Reconnect both USB adapters, then check:"
echo "  ls -l /dev/bmw-ibus /dev/bmw-obd"
echo
echo "Expected device names:"
echo "  /dev/bmw-ibus"
echo "  /dev/bmw-obd"
