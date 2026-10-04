from __future__ import annotations

from qtile_settings.adapters import commands, network


def test_network_get_active_connection(monkeypatch):
    # Mock nmcli device output
    def fake_run_command(cmd, timeout=15):
        if "device" in cmd and "wifi" in cmd and "list" in cmd:
            return commands.CommandResult(
                ok=True,
                stdout="*:Qtile_Mock_5G:75:WPA2:▂▄▆█:5320 MHz\n :Neighbor_Net:45:WPA2:▂▄__:2412 MHz",
                error="",
            )
        if "device" in cmd and "show" in cmd:
            return commands.CommandResult(
                ok=True,
                stdout=(
                    "GENERAL.DEVICE:wlp2s0\n"
                    "GENERAL.TYPE:wifi\n"
                    "GENERAL.HWADDR:02:00:00:00:00:01\n"
                    "IP4.ADDRESS[1]:192.168.1.50/24\n"
                    "IP4.GATEWAY:192.168.1.1\n"
                    "IP4.DNS[1]:1.1.1.1\n"
                ),
                error="",
            )
        if "device" in cmd:
            return commands.CommandResult(
                ok=True,
                stdout="wlp2s0:wifi:connected:Qtile_Mock_5G\nlo:loopback:connected:lo\n",
                error="",
            )
        if "radio" in cmd:
            return commands.CommandResult(ok=True, stdout="enabled\n", error="")
        return commands.CommandResult(ok=True, stdout="", error="")

    monkeypatch.setattr(network, "run_command", fake_run_command)
    monkeypatch.setattr(network.shutil, "which", lambda cmd: f"/usr/bin/{cmd}")

    info = network.get_active_connection()
    assert info["connected"] is True
    assert info["name"] == "Qtile_Mock_5G"
    assert info["type"] == "wifi"
    assert info["ip_address"] == "192.168.1.50/24"
    assert info["gateway"] == "192.168.1.1"
    assert "1.1.1.1" in info["dns"]
    assert info["signal_percent"] == 75

    radio = network.get_wifi_radio_enabled()
    assert radio is True

    aps = network.scan_wifi_networks()
    assert len(aps) == 2
    assert aps[0]["ssid"] == "Qtile_Mock_5G"
    assert aps[0]["in_use"] is True


def test_network_fallback_ip(monkeypatch):
    monkeypatch.setattr(network.shutil, "which", lambda cmd: None)

    def fake_run(cmd, timeout=15):
        if "route" in cmd:
            return commands.CommandResult(
                ok=True,
                stdout="default via 192.168.1.1 dev enp1s0 proto dhcp",
                error="",
            )
        if "address" in cmd:
            return commands.CommandResult(
                ok=True,
                stdout="enp1s0 UP 192.168.1.100/24",
                error="",
            )
        return commands.CommandResult(ok=False, stdout="", error="no")

    monkeypatch.setattr(network, "run_command", fake_run)

    info = network.get_active_connection()
    assert info["connected"] is True
    assert info["gateway"] == "192.168.1.1"
    assert info["device"] == "enp1s0"
    assert info["ip_address"] == "192.168.1.100/24"


def test_network_wifi_deduplication_and_band_label(monkeypatch):
    nmcli_output = (
        "*:Home_WiFi:80:WPA2:▂▄▆█:5180 MHz\n"
        " :Home_WiFi:65:WPA2:▂▄▆_:2412 MHz\n"
        " :Neighbor_Net:50:WPA2:▂▄__:2437 MHz\n"
        " :--:30:WPA2:▂___:2412 MHz\n"
        " ::::20:WPA2:____:5240 MHz\n"
        " ::15:WPA2:____:2462 MHz\n"
    )
    monkeypatch.setattr(network.shutil, "which", lambda cmd: f"/usr/bin/{cmd}")
    monkeypatch.setattr(
        network,
        "run_command",
        lambda cmd, timeout=15: commands.CommandResult(ok=True, stdout=nmcli_output, error=""),
    )

    aps = network.scan_wifi_networks()
    # Hidden networks (-- and empty) should be eliminated
    assert len(aps) == 2
    # Active network pinned to top
    assert aps[0]["ssid"] == "Home_WiFi"
    assert aps[0]["in_use"] is True
    # Highest signal kept
    assert aps[0]["signal"] == 80
    # Both bands combined into clean label
    assert aps[0]["band_label"] == "2.4 GHz / 5 GHz"

    assert aps[1]["ssid"] == "Neighbor_Net"
    assert aps[1]["band_label"] == "2.4 GHz"
