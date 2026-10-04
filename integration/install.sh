#!/usr/bin/env bash
# ==============================================================================
# Qtile Settings & Command Center - Idempotent Multi-OS Installer
# Supports Debian/Ubuntu, Arch, Fedora, openSUSE, Void, Solus, Gentoo, FreeBSD, NixOS
# ==============================================================================
set -euo pipefail

# ------------------------------------------------------------------------------
# 1. Canonical Script & Repository Resolution
# ------------------------------------------------------------------------------
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

if [ -f "${SCRIPT_DIR}/pyproject.toml" ]; then
    REPO_DIR="${SCRIPT_DIR}"
elif [ -f "${SCRIPT_DIR}/../pyproject.toml" ]; then
    REPO_DIR="$(cd -P "${SCRIPT_DIR}/.." && pwd)"
else
    REPO_DIR="${PWD}"
fi

# ------------------------------------------------------------------------------
# 2. CLI Flags & Options
# ------------------------------------------------------------------------------
DRY_RUN=0
ASSUME_YES=0
INSTALL_DEPS=0
NO_DEPS=0

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --yes|-y) ASSUME_YES=1 ;;
        --install-deps) INSTALL_DEPS=1 ;;
        --no-deps) NO_DEPS=1 ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --install-deps   Install system dependencies using detected package manager (requires sudo)"
            echo "  --no-deps        Skip system package dependency checks/installation"
            echo "  --dry-run        Show detected OS, planned actions, and exit without changes"
            echo "  --yes, -y        Non-interactive mode (automatically accept defaults)"
            echo "  -h, --help       Display this help message and exit"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 2
            ;;
    esac
done

echo "=================================================================="
echo " Qtile Settings & Command Center - Installer"
echo " Source: ${REPO_DIR}"
echo "=================================================================="

# ------------------------------------------------------------------------------
# 3. Multi-OS & Package Manager Detection (Matches Qtile-Con Matrix)
# ------------------------------------------------------------------------------
OS_ID="unknown"
OS_LIKE=""
OS_NAME="Unknown Linux"
PM=""
PM_FAMILY=""

if [[ "$(uname -s)" == "FreeBSD" ]]; then
    OS_ID="freebsd"
    OS_NAME="FreeBSD"
    PM="pkg"
    PM_FAMILY="freebsd"
elif [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_ID="${ID:-unknown}"
    OS_LIKE="${ID_LIKE:-}"
    OS_NAME="${PRETTY_NAME:-$OS_ID}"
fi

if [[ -z "$PM" ]]; then
    case "$OS_ID" in
        debian|ubuntu|linuxmint|pop|parrot|kali|raspbian)
            PM="apt"
            PM_FAMILY="debian"
            ;;
        arch|manjaro|endeavouros|garuda|artix)
            PM="pacman"
            PM_FAMILY="arch"
            ;;
        fedora|nobara|rhel|centos|rocky|alma)
            PM="dnf"
            PM_FAMILY="fedora"
            ;;
        opensuse*|suse)
            PM="zypper"
            PM_FAMILY="suse"
            ;;
        solus)
            PM="eopkg"
            PM_FAMILY="solus"
            ;;
        void)
            PM="xbps"
            PM_FAMILY="void"
            ;;
        gentoo)
            PM="emerge"
            PM_FAMILY="gentoo"
            ;;
        nixos)
            PM="nix"
            PM_FAMILY="nixos"
            ;;
        freebsd)
            PM="pkg"
            PM_FAMILY="freebsd"
            ;;
        *)
            if [[ "$OS_LIKE" =~ (debian|ubuntu) ]]; then PM="apt"; PM_FAMILY="debian";
            elif [[ "$OS_LIKE" =~ (arch) ]]; then PM="pacman"; PM_FAMILY="arch";
            elif [[ "$OS_LIKE" =~ (fedora|rhel) ]]; then PM="dnf"; PM_FAMILY="fedora";
            elif [[ "$OS_LIKE" =~ (suse) ]]; then PM="zypper"; PM_FAMILY="suse";
            elif [[ "$OS_LIKE" =~ (void) ]]; then PM="xbps"; PM_FAMILY="void";
            elif [[ "$OS_LIKE" =~ (gentoo) ]]; then PM="emerge"; PM_FAMILY="gentoo";
            elif command -v apt-get >/dev/null 2>&1; then PM="apt"; PM_FAMILY="debian";
            elif command -v pacman >/dev/null 2>&1; then PM="pacman"; PM_FAMILY="arch";
            elif command -v dnf >/dev/null 2>&1; then PM="dnf"; PM_FAMILY="fedora";
            elif command -v zypper >/dev/null 2>&1; then PM="zypper"; PM_FAMILY="suse";
            elif command -v xbps-install >/dev/null 2>&1; then PM="xbps"; PM_FAMILY="void";
            elif command -v emerge >/dev/null 2>&1; then PM="emerge"; PM_FAMILY="gentoo";
            elif command -v eopkg >/dev/null 2>&1; then PM="eopkg"; PM_FAMILY="solus";
            elif command -v nix-env >/dev/null 2>&1 || [ -f /etc/NIXOS ]; then PM="nix"; PM_FAMILY="nixos";
            elif command -v pkg >/dev/null 2>&1; then PM="pkg"; PM_FAMILY="freebsd";
            fi
            ;;
    esac
fi

echo "[✓] Operating System: ${OS_NAME} (${OS_ID})"
echo "[✓] Package Manager:  ${PM:-None detected}"

if [[ "$PM_FAMILY" == "nixos" ]]; then
    echo ""
    echo "[*] NixOS detected! You can install or run directly with flakes:"
    echo "    nix run ${REPO_DIR}"
    echo "    nix profile install ${REPO_DIR}"
    echo "    or import the nixosModules/homeManagerModules from flake.nix."
    echo ""
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[!] Dry run mode: exiting without changes."
    exit 0
fi

# ------------------------------------------------------------------------------
# 4. Optional System Dependency Installation
# ------------------------------------------------------------------------------
if [[ "$INSTALL_DEPS" -eq 1 && "$NO_DEPS" -eq 0 && -n "$PM" ]]; then
    echo "==> Installing system dependencies via ${PM}..."
    case "$PM_FAMILY" in
        debian)
            sudo apt-get update -y
            sudo apt-get install -y python3 python3-pip pipx python3-psutil brightnessctl network-manager wireplumber pamixer x11-xserver-utils xinput feh
            ;;
        arch)
            sudo pacman -S --needed --noconfirm python python-pip python-pipx python-psutil brightnessctl networkmanager wireplumber pamixer xorg-xrandr xorg-xinput feh
            ;;
        fedora)
            sudo dnf install -y python3 python3-pip pipx python3-psutil brightnessctl NetworkManager wireplumber pamixer xrandr xinput feh
            ;;
        suse)
            sudo zypper --non-interactive in python3 python3-pip python3-pipx python3-psutil brightnessctl NetworkManager wireplumber pamixer xrandr xinput feh
            ;;
        void)
            sudo xbps-install -y python3 python3-pip pipx python3-psutil brightnessctl NetworkManager wireplumber pamixer xrandr xinput feh
            ;;
        solus)
            sudo eopkg it -y python3 pipx brightnessctl NetworkManager wireplumber pamixer xrandr xinput feh
            ;;
        gentoo)
            sudo emerge --ask=n dev-lang/python dev-python/pip dev-python/pipx dev-python/psutil sys-power/brightnessctl net-misc/networkmanager media-sound/wireplumber x11-apps/xrandr x11-apps/xinput media-gfx/feh
            ;;
        freebsd)
            sudo pkg install -y python3 py311-pip py311-psutil brightnessctl wireplumber pamixer xrandr xinput feh
            ;;
        nixos)
            echo "[*] On NixOS, dependencies are bundled via flake.nix / default.nix."
            ;;
    esac
fi

# ------------------------------------------------------------------------------
# 5. Python Verification & Package Installation with Multi-Tier Fallback
# ------------------------------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo "[-] Error: python3 is required but not installed." >&2
    exit 1
fi

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "[✓] Python ${PYTHON_VERSION} verified."

mkdir -p "${HOME}/.local/bin"
INSTALL_SUCCESS=0

# Tier 1: pipx (Preferred isolated user environment)
if command -v pipx >/dev/null 2>&1; then
    echo "==> [Tier 1] Installing via pipx with system-site-packages..."
    if pipx install --force --system-site-packages "${REPO_DIR}" >/dev/null 2>&1; then
        echo "[✓] Installed into pipx environment."
        INSTALL_SUCCESS=1
    else
        echo "[-] pipx installation encountered an issue; trying fallback..."
    fi
fi

# Tier 2: Dedicated Virtual Environment Fallback
if [[ "$INSTALL_SUCCESS" -eq 0 ]]; then
    echo "==> [Tier 2] Setting up dedicated virtualenv fallback with system-site-packages..."
    VENV_DIR="${REPO_DIR}/.venv"
    if python3 -m venv --system-site-packages "${VENV_DIR}" >/dev/null 2>&1; then
        "${VENV_DIR}/bin/pip" install --upgrade pip >/dev/null 2>&1 || true
        if "${VENV_DIR}/bin/pip" install -e "${REPO_DIR}" >/dev/null 2>&1; then
            ln -sf "${VENV_DIR}/bin/qtile-settings" "${HOME}/.local/bin/qtile-settings"
            echo "[✓] Installed in virtual environment and linked to ~/.local/bin/qtile-settings."
            INSTALL_SUCCESS=1
        fi
    fi
fi

# Tier 3: Direct User Script Wrapper Fallback
if [[ "$INSTALL_SUCCESS" -eq 0 ]]; then
    echo "==> [Tier 3] Creating direct standalone user wrapper script..."
    cat > "${HOME}/.local/bin/qtile-settings" << WRAPPER_EOF
#!/usr/bin/env sh
export PYTHONPATH="${REPO_DIR}/src:\${PYTHONPATH:-}"
exec python3 -m qtile_settings "\$@"
WRAPPER_EOF
    chmod +x "${HOME}/.local/bin/qtile-settings"
    echo "[✓] Standalone runner wrapper created at ~/.local/bin/qtile-settings."
    INSTALL_SUCCESS=1
fi

# ------------------------------------------------------------------------------
# 6. Install XDG Desktop Entries (Rofi / Application Launchers)
# ------------------------------------------------------------------------------
APPS_DIR="${HOME}/.local/share/applications"
mkdir -p "${APPS_DIR}"

INTEGRATION_DIR="${REPO_DIR}/integration"
if [ -f "${INTEGRATION_DIR}/qtile-settings.desktop" ]; then
    cp -f "${INTEGRATION_DIR}/qtile-settings.desktop" "${APPS_DIR}/"
    cp -f "${INTEGRATION_DIR}/qtile-quick-settings.desktop" "${APPS_DIR}/"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "${APPS_DIR}" >/dev/null 2>&1 || true
    fi
    echo "[✓] Desktop application entries registered in ${APPS_DIR}."
fi

# ------------------------------------------------------------------------------
# 7. Integrate Keybindings into Qtile Configuration (Modular & Monolithic Fallbacks)
# ------------------------------------------------------------------------------
KEYS_FILE=""
CONFIG_FILE="${HOME}/.config/qtile/config.py"

if [ -f "${HOME}/.config/qtile/qtile_config/keys.py" ]; then
    KEYS_FILE="${HOME}/.config/qtile/qtile_config/keys.py"
elif [ -f "${HOME}/.config/qtile/keys.py" ]; then
    KEYS_FILE="${HOME}/.config/qtile/keys.py"
elif [ -f "${CONFIG_FILE}" ]; then
    KEYS_FILE="${CONFIG_FILE}"
fi

if [ -n "${KEYS_FILE}" ] && [ -f "${KEYS_FILE}" ]; then
    if grep -q "qtile-settings" "${KEYS_FILE}"; then
        echo "[✓] Qtile keybindings already configured in ${KEYS_FILE} (idempotent)."
    else
        echo "==> Configuring Qtile keybindings in ${KEYS_FILE}..."
        BACKUP_FILE="${KEYS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "${KEYS_FILE}" "${BACKUP_FILE}"
        echo "[✓] Created backup: ${BACKUP_FILE}"

        cat >> "${KEYS_FILE}" << 'KEY_EOF'

# ==============================================================================
# QTILE SETTINGS INTEGRATION (Auto-generated by install.sh)
# ==============================================================================
try:
    keys.extend([
        Key([MOD], "s", lazy.spawn("qtile-settings"), desc="Open Qtile Settings & Command Center"),
        Key([MOD, "shift"], "s", lazy.spawn("qtile-settings --quick"), desc="Open Qtile Quick Settings"),
    ])
except Exception:
    pass
KEY_EOF

        # Validate Qtile configuration after adding keys
        if command -v qtile >/dev/null 2>&1 && [ -f "${CONFIG_FILE}" ]; then
            echo "==> Verifying Qtile configuration syntax..."
            if qtile check -c "${CONFIG_FILE}" >/dev/null 2>&1; then
                echo "[✓] Qtile configuration syntax validated successfully."
            else
                echo "[-] Warning: Qtile check reported an error. Rolling back ${KEYS_FILE}..." >&2
                cp "${BACKUP_FILE}" "${KEYS_FILE}"
                echo "[✓] Restored backup."
            fi
        fi
    fi
fi

# ------------------------------------------------------------------------------
# 8. Check PATH Environment
# ------------------------------------------------------------------------------
case ":${PATH}:" in
    *:"${HOME}/.local/bin":*) ;;
    *)
        echo ""
        echo "[!] NOTE: ${HOME}/.local/bin is not in your \$PATH."
        echo "    Add this to your ~/.bashrc or ~/.zshrc:"
        echo "    export PATH=\"\${HOME}/.local/bin:\${PATH}\""
        ;;
esac

echo ""
echo "=================================================================="
echo " [✓] Qtile Settings installation completed successfully!"
echo "     • Open GUI Command Center: qtile-settings"
echo "     • Open Quick Settings popup: qtile-settings --quick"
echo "     • Keybinding (Full Settings):  Super + S"
echo "     • Keybinding (Quick Settings): Super + Shift + S"
echo "=================================================================="
