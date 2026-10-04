from __future__ import annotations

from qtile_settings.adapters import commands, input_devices


def test_get_touchpad_status_unavailable(monkeypatch):
    monkeypatch.setattr(input_devices.shutil, "which", lambda cmd: None)
    status = input_devices.get_touchpad_status()
    assert not status.available


def test_get_touchpad_status_parsed(monkeypatch):
    monkeypatch.setattr(input_devices.shutil, "which", lambda cmd: "/usr/bin/xinput")

    def mock_run(argv, **kwargs):
        if argv == ["xinput", "list"]:
            return commands.CommandResult(
                True,
                stdout="⎡ Virtual core pointer\n"
                       "⎜   ↳ Test Touchpad id=12 [slave pointer]\n",
            )
        if argv == ["xinput", "list-props", "12"]:
            return commands.CommandResult(
                True,
                stdout="libinput Tapping Enabled (300): 1\n"
                       "libinput Natural Scrolling Enabled (305): 1\n"
                       "libinput Click Method Enabled (310): 0, 1\n",
            )
        return commands.CommandResult(False, error="Unknown command")

    monkeypatch.setattr(input_devices, "run_command", mock_run)
    status = input_devices.get_touchpad_status()
    assert status.available
    assert status.device_id == "12"
    assert status.tapping_enabled
    assert status.natural_scrolling


def test_set_touchpad_property_unknown():
    ok, _ = input_devices.set_touchpad_property("unknown_prop", True)
    assert not ok


def test_kbd_backlight_detection_and_get(monkeypatch):
    def mock_run(argv, **kwargs):
        if argv == ["brightnessctl", "--list"]:
            return commands.CommandResult(
                True,
                stdout="Device 'smc::kbd_backlight' of class 'leds':\n\tCurrent brightness: 102 (40%)\n\tMax brightness: 255\n",
            )
        if argv == ["brightnessctl", "--device=smc::kbd_backlight", "info"]:
            return commands.CommandResult(
                True,
                stdout="Device 'smc::kbd_backlight' of class 'leds':\n\tCurrent brightness: 102 (40%)\n\tMax brightness: 255\n",
            )
        return commands.CommandResult(False, error="Unknown command")

    monkeypatch.setattr(input_devices.shutil, "which", lambda cmd: "/usr/bin/brightnessctl")
    monkeypatch.setattr(input_devices, "run_command", mock_run)

    assert input_devices.find_kbd_backlight_device() == "smc::kbd_backlight"
    assert input_devices.has_kbd_backlight() is True
    val, dev = input_devices.get_kbd_backlight()
    assert val == 40
    assert dev == "smc::kbd_backlight"


def test_kbd_backlight_set(monkeypatch):
    ran_cmds = []

    def mock_run(argv, **kwargs):
        ran_cmds.append(argv)
        if argv == ["brightnessctl", "--list"]:
            return commands.CommandResult(
                True,
                stdout="Device 'smc::kbd_backlight' of class 'leds':\n",
            )
        if argv == ["brightnessctl", "--device=smc::kbd_backlight", "set", "60%"]:
            return commands.CommandResult(True, stdout="Updated device")
        return commands.CommandResult(False, error="Unknown command")

    monkeypatch.setattr(input_devices.shutil, "which", lambda cmd: "/usr/bin/brightnessctl")
    monkeypatch.setattr(input_devices, "run_command", mock_run)

    ok, msg = input_devices.set_kbd_backlight(60)
    assert ok is True
    assert "60%" in msg
    assert ["brightnessctl", "--device=smc::kbd_backlight", "set", "60%"] in ran_cmds


def test_kbd_backlight_no_device(monkeypatch):
    monkeypatch.setattr(input_devices.shutil, "which", lambda cmd: None)
    monkeypatch.setattr(input_devices.Path, "exists", lambda self: False)

    assert input_devices.find_kbd_backlight_device() is None
    assert input_devices.has_kbd_backlight() is False
    val, _ = input_devices.get_kbd_backlight()
    assert val is None
    ok, _ = input_devices.set_kbd_backlight(50)
    assert ok is False

