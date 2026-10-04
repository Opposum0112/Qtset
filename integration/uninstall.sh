#!/usr/bin/env bash
# ==============================================================================
# Qtile Settings & Command Center - Idempotent Uninstaller
# Supports standard clean removal and complete '--purge'
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
PURGE=0

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --yes|-y) ASSUME_YES=1 ;;
        --purge|--all) PURGE=1 ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --purge, --all    Purge all configuration backups, caches, and fallback virtualenvs"
            echo "  --dry-run         Preview actions without modifying or removing any files"
            echo "  --yes, -y         Skip interactive confirmations"
            echo "  -h, --help        Display this help message and exit"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 2
            ;;
    esac
done

echo "=================================================================="
echo " Qtile Settings & Command Center - Uninstaller"
echo " Mode: $([ "$PURGE" -eq 1 ] && echo "FULL PURGE" || echo "Standard Clean Removal")"
echo "=================================================================="

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[!] Dry-run mode active. No files will be deleted."
fi

# ------------------------------------------------------------------------------
# 3. Uninstall Package & Binary Links
# ------------------------------------------------------------------------------
if command -v pipx >/dev/null 2>&1; then
    if pipx list 2>/dev/null | grep -q "package qtile-settings"; then
        echo "==> Removing pipx package 'qtile-settings'..."
        if [[ "$DRY_RUN" -eq 0 ]]; then
            pipx uninstall qtile-settings >/dev/null 2>&1 || true
            echo "[✓] pipx package uninstalled."
        else
            echo "[dry-run] Would run: pipx uninstall qtile-settings"
        fi
    fi
fi

TARGET_BIN="${HOME}/.local/bin/qtile-settings"
if [ -L "${TARGET_BIN}" ] || [ -f "${TARGET_BIN}" ]; then
    echo "==> Removing ${TARGET_BIN}..."
    if [[ "$DRY_RUN" -eq 0 ]]; then
        rm -f "${TARGET_BIN}"
        echo "[✓] Removed ${TARGET_BIN}."
    else
        echo "[dry-run] Would remove: ${TARGET_BIN}"
    fi
fi

# ------------------------------------------------------------------------------
# 4. Remove XDG Desktop Entries
# ------------------------------------------------------------------------------
APPS_DIR="${HOME}/.local/share/applications"
REMOVED_DESKTOP=0

for desktop_file in "qtile-settings.desktop" "qtile-quick-settings.desktop"; do
    target="${APPS_DIR}/${desktop_file}"
    if [ -f "${target}" ]; then
        echo "==> Removing ${target}..."
        if [[ "$DRY_RUN" -eq 0 ]]; then
            rm -f "${target}"
            REMOVED_DESKTOP=1
        else
            echo "[dry-run] Would remove: ${target}"
        fi
    fi
done

if [ "${REMOVED_DESKTOP}" -eq 1 ] && [[ "$DRY_RUN" -eq 0 ]]; then
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "${APPS_DIR}" >/dev/null 2>&1 || true
    fi
    echo "[✓] Removed desktop application entries and refreshed database."
fi

# ------------------------------------------------------------------------------
# 5. Clean up Qtile Keybinding Integration Block
# ------------------------------------------------------------------------------
CONFIG_DIR="${HOME}/.config/qtile"
CONFIG_FILE="${CONFIG_DIR}/config.py"

for candidate in "${CONFIG_DIR}/qtile_config/keys.py" "${CONFIG_DIR}/keys.py" "${CONFIG_FILE}"; do
    if [ -f "${candidate}" ] && grep -q "QTILE SETTINGS INTEGRATION" "${candidate}"; then
        echo "==> Reverting keybinding block in ${candidate}..."
        if [[ "$DRY_RUN" -eq 0 ]]; then
            BACKUP_FILE="${candidate}.backup.uninstall.$(date +%Y%m%d_%H%M%S)"
            cp "${candidate}" "${BACKUP_FILE}"
            echo "[✓] Created backup: ${BACKUP_FILE}"

            python3 - << PYEOF
import os

target_path = os.path.expanduser("${candidate}")
if os.path.exists(target_path):
    with open(target_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "QTILE SETTINGS INTEGRATION" in content:
        lines = content.splitlines()
        filtered = []
        skip = False
        for line in lines:
            if "QTILE SETTINGS INTEGRATION" in line:
                if filtered and filtered[-1].strip().startswith("# ==="):
                    filtered.pop()
                skip = True
                continue
            if skip:
                if line.strip() == "pass":
                    skip = False
                continue
            filtered.append(line)
        new_content = "\n".join(filtered).strip() + "\n"
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_content)
PYEOF
            echo "[✓] Cleaned keybindings from ${candidate}."

            # Verify configuration after stripping
            if command -v qtile >/dev/null 2>&1 && [ -f "${CONFIG_FILE}" ]; then
                echo "==> Validating Qtile configuration syntax..."
                if qtile check -c "${CONFIG_FILE}" >/dev/null 2>&1; then
                    echo "[✓] Qtile configuration validated successfully."
                else
                    echo "[-] Warning: Qtile check reported an issue. Restoring backup..." >&2
                    cp "${BACKUP_FILE}" "${candidate}"
                fi
            fi
        else
            echo "[dry-run] Would strip QTILE SETTINGS INTEGRATION from: ${candidate}"
        fi
        break
    fi
done

# ------------------------------------------------------------------------------
# 6. Cache Directory Cleanup
# ------------------------------------------------------------------------------
CACHE_DIR="${HOME}/.cache/qtile-settings"
if [ -d "${CACHE_DIR}" ]; then
    echo "==> Removing cache directory ${CACHE_DIR}..."
    if [[ "$DRY_RUN" -eq 0 ]]; then
        rm -rf "${CACHE_DIR}"
        echo "[✓] Cleaned cache directory."
    else
        echo "[dry-run] Would remove: ${CACHE_DIR}"
    fi
fi

# ------------------------------------------------------------------------------
# 7. Complete Purge Actions (--purge flag)
# ------------------------------------------------------------------------------
if [[ "$PURGE" -eq 1 ]]; then
    echo ""
    echo "==> Executing PURGE cleanup..."

    # Purge timestamped backups created by Qtile Settings
    if [ -d "${CONFIG_DIR}" ]; then
        echo "==> Purging Qtile Settings backup files in ${CONFIG_DIR}..."
        if [[ "$DRY_RUN" -eq 0 ]]; then
            # Find and remove backups created by qtile-settings installer and runtime
            find "${CONFIG_DIR}" -maxdepth 2 -type f \( -name "*.backup.*" -o -name "*.backup" \) -exec rm -f {} +
            echo "[✓] Configuration backups purged."
        else
            echo "[dry-run] Would remove all *.backup.* in ${CONFIG_DIR}"
        fi
    fi

    # Purge dedicated virtual environment if one was created in REPO_DIR
    VENV_DIR="${REPO_DIR}/.venv"
    if [ -d "${VENV_DIR}" ]; then
        echo "==> Purging fallback virtualenv at ${VENV_DIR}..."
        if [[ "$DRY_RUN" -eq 0 ]]; then
            rm -rf "${VENV_DIR}"
            echo "[✓] Removed ${VENV_DIR}."
        else
            echo "[dry-run] Would remove: ${VENV_DIR}"
        fi
    fi

    echo "[✓] Purge complete: all associated backups and runtime artifacts removed."
fi

echo ""
echo "=================================================================="
echo " [✓] Qtile Settings uninstallation completed cleanly."
echo "=================================================================="
