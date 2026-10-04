"""Network and wireless connectivity adapter.

Interfaces with NetworkManager via `nmcli` to inspect active connections, query
IPv4/gateway/DNS parameters, toggle the Wi-Fi radio, perform access point scans with
frequency band consolidation, and list network interfaces with robust fallbacks to `ip`.
"""

from __future__ import annotations

import re
import shutil
from typing import Any

from qtile_settings.adapters.commands import run_command


def _unescape_nmcli(field: str) -> str:
    """Unescape backslash-escaped characters from nmcli terse output."""
    return field.replace(r"\:", ":").replace(r"\\", "\\").strip()


def get_wifi_radio_enabled() -> bool:
    """Check if Wi-Fi radio is currently enabled in NetworkManager."""
    if not shutil.which("nmcli"):
        return False
    res = run_command(["nmcli", "radio", "wifi"])
    if not res.ok:
        return False
    return res.stdout.strip().lower() == "enabled"


def set_wifi_radio(enabled: bool) -> tuple[bool, str]:
    """Turn Wi-Fi radio on or off."""
    if not shutil.which("nmcli"):
        return False, "nmcli is not installed"
    state = "on" if enabled else "off"
    res = run_command(["nmcli", "radio", "wifi", state])
    return res.ok, res.stdout or res.error or f"Wi-Fi turned {state}"


def get_active_connection() -> dict[str, Any]:
    """Retrieve detailed information about the primary active network connection."""
    info: dict[str, Any] = {
        "connected": False,
        "name": "Disconnected",
        "type": "none",
        "device": "",
        "ip_address": "",
        "gateway": "",
        "dns": [],
        "hw_addr": "",
        "signal_percent": 0,
        "signal_bars": "",
        "frequency": "",
        "security": "",
    }

    if not shutil.which("nmcli"):
        # Fallback to ip route / ip addr if nmcli is missing
        _populate_ip_fallback(info)
        return info

    dev_res = run_command(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"])
    if not dev_res.ok or not dev_res.stdout:
        _populate_ip_fallback(info)
        return info

    active_dev = ""
    active_type = ""
    active_conn = ""

    for line in dev_res.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 4 and "connected" in parts[2].lower() and parts[1] not in ("loopback", "bridge"):
            active_dev = parts[0]
            active_type = parts[1]
            active_conn = parts[3]
            break

    if not active_dev:
        return info

    info["connected"] = True
    info["name"] = active_conn
    info["type"] = active_type
    info["device"] = active_dev

    # Detailed device query
    show_res = run_command([
        "nmcli", "-t", "-f",
        "GENERAL.DEVICE,GENERAL.TYPE,GENERAL.HWADDR,IP4.ADDRESS,IP4.GATEWAY,IP4.DNS",
        "device", "show", active_dev
    ])
    if show_res.ok and show_res.stdout:
        for line in show_res.stdout.splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            if k == "GENERAL.HWADDR":
                info["hw_addr"] = v
            elif k.startswith("IP4.ADDRESS") and not info["ip_address"]:
                info["ip_address"] = v
            elif k == "IP4.GATEWAY":
                info["gateway"] = v
            elif k.startswith("IP4.DNS") and v and v not in info["dns"]:
                info["dns"].append(v)

    # If it's wifi, fetch active Wi-Fi signal & details
    if active_type == "wifi":
        wifi_res = run_command(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY,BARS,FREQ", "device", "wifi", "list"])
        if wifi_res.ok and wifi_res.stdout:
            for line in wifi_res.stdout.splitlines():
                if line.startswith("*"):
                    # Active AP
                    parts = line.split(":")
                    if len(parts) >= 6:
                        # parts: ['*', ssid, signal, security, bars, freq]
                        info["signal_percent"] = int(parts[2]) if parts[2].isdigit() else 0
                        info["security"] = parts[3]
                        info["signal_bars"] = parts[4]
                        info["frequency"] = parts[5]
                    break

    return info


def _populate_ip_fallback(info: dict[str, Any]) -> None:
    """Fallback reader using ip route and ip address commands."""
    route_res = run_command(["ip", "route", "show", "default"])
    if route_res.ok and route_res.stdout:
        # e.g.: default via 192.168.1.254 dev wlp2s0 proto dhcp metric 600
        match = re.search(r"default via (\S+) dev (\S+)", route_res.stdout)
        if match:
            info["connected"] = True
            info["gateway"] = match.group(1)
            info["device"] = match.group(2)
            info["name"] = match.group(2)
            info["type"] = "wifi" if "wl" in match.group(2) else "ethernet"

    if info["device"]:
        addr_res = run_command(["ip", "-brief", "address", "show", info["device"]])
        if addr_res.ok and addr_res.stdout:
            # e.g.: wlp2s0 UP 192.168.1.12/24 fe80::...
            tokens = addr_res.stdout.split()
            if len(tokens) >= 3:
                info["ip_address"] = tokens[2]


def scan_wifi_networks() -> list[dict[str, Any]]:
    """Scan and list available Wi-Fi access points with clean SSIDs and band information."""
    if not shutil.which("nmcli"):
        return []
    res = run_command(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY,BARS,FREQ", "device", "wifi", "list"])
    if not res.ok or not res.stdout:
        return []

    networks_by_ssid: dict[str, dict[str, Any]] = {}

    for line in res.stdout.splitlines():
        if not line:
            continue
        in_use = line.startswith("*")
        raw_parts = re.split(r"(?<!\\):", line)
        if len(raw_parts) < 6:
            continue
        ssid = _unescape_nmcli(raw_parts[1])
        # Skip hidden or empty SSIDs
        if not ssid or ssid in ("--", "::"):
            continue

        signal = int(raw_parts[2]) if raw_parts[2].isdigit() else 0
        security = _unescape_nmcli(raw_parts[3]) or "Open"
        bars = raw_parts[4].strip()
        freq_str = raw_parts[5].strip()

        # Determine band
        freq_nums = re.findall(r"\d+", freq_str)
        freq_mhz = int(freq_nums[0]) if freq_nums else 0
        band = "5 GHz" if freq_mhz >= 4000 else "2.4 GHz"

        if ssid not in networks_by_ssid:
            networks_by_ssid[ssid] = {
                "in_use": in_use,
                "ssid": ssid,
                "signal": signal,
                "bars": bars,
                "security": security,
                "bands": {band},
                "freq": freq_str,
            }
        else:
            existing = networks_by_ssid[ssid]
            if in_use:
                existing["in_use"] = True
            if signal > existing["signal"]:
                existing["signal"] = signal
                existing["bars"] = bars
                existing["freq"] = freq_str
            existing["bands"].add(band)

    # Convert to list and format band string
    networks = []
    for item in networks_by_ssid.values():
        bands_list = sorted(item["bands"])
        item["band_label"] = " / ".join(bands_list)
        networks.append(item)

    # Sort: in-use first, then highest signal
    networks.sort(key=lambda n: (not n["in_use"], -n["signal"]))
    return networks


def list_all_interfaces() -> list[dict[str, Any]]:
    """List all detected network interfaces with state and IP address."""
    interfaces: list[dict[str, Any]] = []
    if shutil.which("nmcli"):
        dev_res = run_command(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"])
        if dev_res.ok and dev_res.stdout:
            for line in dev_res.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 4:
                    dev = parts[0]
                    itype = parts[1]
                    state = parts[2]
                    conn = parts[3] or "--"
                    interfaces.append({
                        "device": dev,
                        "type": itype,
                        "state": state,
                        "connection": conn,
                    })
            return interfaces

    # Fallback to ip -brief link
    ip_res = run_command(["ip", "-brief", "address", "show"])
    if ip_res.ok and ip_res.stdout:
        for line in ip_res.stdout.splitlines():
            tokens = line.split()
            if tokens:
                interfaces.append({
                    "device": tokens[0],
                    "type": "wireless" if "wl" in tokens[0] else ("loopback" if tokens[0] == "lo" else "ethernet"),
                    "state": tokens[1] if len(tokens) > 1 else "UNKNOWN",
                    "connection": tokens[2] if len(tokens) > 2 else "--",
                })

    return interfaces


def rescan_wifi() -> tuple[bool, str]:
    """Force NetworkManager to rescan available Wi-Fi access points."""
    if not shutil.which("nmcli"):
        return False, "nmcli is not installed"
    res = run_command(["nmcli", "device", "wifi", "rescan"])
    return res.ok, res.stdout or res.error or "Wi-Fi rescan requested"


def connect_wifi(ssid: str, password: str = "") -> tuple[bool, str]:
    """Connect to a Wi-Fi network using nmcli."""
    if not shutil.which("nmcli"):
        return False, "nmcli is not installed"
    cmd = ["nmcli", "device", "wifi", "connect", ssid]
    if password:
        cmd.extend(["password", password])
    res = run_command(cmd, timeout=25)
    return res.ok, res.stdout or res.error or f"Connected to {ssid}"


def network_status() -> str:
    """Return concise raw network device overview for legacy diagnostics."""
    if shutil.which("nmcli"):
        result = run_command(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"])
        if result.ok:
            return result.stdout or "No NetworkManager devices found."
    return "NetworkManager CLI (nmcli) is not available."
