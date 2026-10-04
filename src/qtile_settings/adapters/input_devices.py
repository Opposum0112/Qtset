"""Hardware input and illumination adapter.

Controls libinput touchpad gestures (tapping, natural scrolling, click methods via xinput),
display backlight brightness (via brightnessctl/xbacklight), and hardware keyboard key
illumination (Apple SMC and Linux /sys/class/leds subsystems).
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from qtile_settings.adapters.commands import run_command


@dataclass
class TouchpadStatus:
    available: bool
    device_id: str | None = None
    device_name: str = "None"
    tapping_enabled: bool = False
    natural_scrolling: bool = False
    clickfinger_enabled: bool = False


def get_touchpad_status() -> TouchpadStatus:
    if not shutil.which("xinput"):
        return TouchpadStatus(available=False)

    list_res = run_command(["xinput", "list"])
    if not list_res.ok:
        return TouchpadStatus(available=False)

    touchpad_id: str | None = None
    touchpad_name: str = "Unknown"

    # Search for pointer devices that have libinput Tapping Enabled property
    id_matches = re.findall(r"id=(\d+)", list_res.stdout)
    for dev_id in id_matches:
        props = run_command(["xinput", "list-props", dev_id])
        if props.ok and "libinput Tapping Enabled (" in props.stdout:
            touchpad_id = dev_id
            name_m = re.search(rf"↳\s*([^\t\n]+?)\s*id={dev_id}\b", list_res.stdout)
            if name_m:
                touchpad_name = name_m.group(1).strip()
            break

    if not touchpad_id:
        return TouchpadStatus(available=False)

    props = run_command(["xinput", "list-props", touchpad_id])
    if not props.ok:
        return TouchpadStatus(available=True, device_id=touchpad_id, device_name=touchpad_name)

    tapping = bool(re.search(r"libinput Tapping Enabled \(\d+\):\s*1", props.stdout))
    natural = bool(re.search(r"libinput Natural Scrolling Enabled \(\d+\):\s*1", props.stdout))
    clickfinger = bool(re.search(r"libinput Click Method Enabled \(\d+\):\s*0,\s*1", props.stdout))

    return TouchpadStatus(
        available=True,
        device_id=touchpad_id,
        device_name=touchpad_name,
        tapping_enabled=tapping,
        natural_scrolling=natural,
        clickfinger_enabled=clickfinger,
    )


def set_touchpad_property(prop_name: str, enabled: bool) -> tuple[bool, str]:
    status = get_touchpad_status()
    if not status.available or not status.device_id:
        return False, "No libinput touchpad found"

    val = "1" if enabled else "0"
    prop_map = {
        "tapping": "libinput Tapping Enabled",
        "natural_scrolling": "libinput Natural Scrolling Enabled",
    }
    target = prop_map.get(prop_name)
    if not target:
        return False, f"Unknown touchpad property: {prop_name}"

    res = run_command(["xinput", "set-prop", status.device_id, target, val])
    return res.ok, res.error or f"{prop_name} set to {'enabled' if enabled else 'disabled'}"


def get_brightness() -> tuple[int | None, str]:
    """Return brightness percentage (0-100) and any status message."""
    if shutil.which("brightnessctl"):
        res = run_command(["brightnessctl", "info"])
        if res.ok:
            m = re.search(r"\((\d+)%\)", res.stdout)
            if m:
                return int(m.group(1)), ""
    if shutil.which("xbacklight"):
        res = run_command(["xbacklight", "-get"])
        if res.ok:
            try:
                return round(float(res.stdout)), ""
            except ValueError:
                pass
    return None, "Brightness control not available"


def set_brightness(percent: int) -> tuple[bool, str]:
    percent = max(1, min(100, int(percent)))
    if shutil.which("brightnessctl"):
        res = run_command(["brightnessctl", "set", f"{percent}%"])
        return res.ok, res.error or f"Brightness set to {percent}%"
    if shutil.which("xbacklight"):
        res = run_command(["xbacklight", "-set", str(percent)])
        return res.ok, res.error or f"Brightness set to {percent}%"
    return False, "No brightness control tool found"


def find_kbd_backlight_device() -> str | None:
    """Find the device name for keyboard backlight (e.g. smc::kbd_backlight)."""
    if shutil.which("brightnessctl"):
        res = run_command(["brightnessctl", "--list"])
        if res.ok:
            matches = re.findall(r"Device '([^']+)' of class 'leds':", res.stdout)
            for dev in matches:
                if "kbd" in dev.lower() or "keyboard" in dev.lower():
                    return dev

    leds_path = Path("/sys/class/leds")
    if leds_path.exists():
        try:
            for p in leds_path.iterdir():
                if "kbd" in p.name.lower() or "keyboard" in p.name.lower():
                    return p.name
        except OSError:
            return None
    return None


def has_kbd_backlight() -> bool:
    """Return True if a controllable keyboard backlight device is detected."""
    return find_kbd_backlight_device() is not None


def get_kbd_backlight() -> tuple[int | None, str]:
    """Return keyboard backlight percentage (0-100) and device name or error message."""
    dev = find_kbd_backlight_device()
    if not dev:
        return None, "No keyboard backlight device detected"

    if shutil.which("brightnessctl"):
        res = run_command(["brightnessctl", f"--device={dev}", "info"])
        if res.ok:
            m = re.search(r"\((\d+)%\)", res.stdout)
            if m:
                return int(m.group(1)), dev

    # Direct sysfs fallback
    try:
        b_file = Path(f"/sys/class/leds/{dev}/brightness")
        m_file = Path(f"/sys/class/leds/{dev}/max_brightness")
        if b_file.exists() and m_file.exists():
            cur = int(b_file.read_text().strip())
            max_val = int(m_file.read_text().strip())
            if max_val > 0:
                pct = round((cur / max_val) * 100)
                return pct, dev
    except OSError:
        return None, "Unable to read keyboard backlight level"

    return None, "Unable to read keyboard backlight level"


def set_kbd_backlight(percent: int) -> tuple[bool, str]:
    """Set keyboard backlight brightness percentage (0-100)."""
    percent = max(0, min(100, int(percent)))
    dev = find_kbd_backlight_device()
    if not dev:
        return False, "No keyboard backlight device detected"

    if shutil.which("brightnessctl"):
        res = run_command(["brightnessctl", f"--device={dev}", "set", f"{percent}%"])
        if res.ok:
            return True, f"Keyboard backlight set to {percent}%"

    try:
        b_file = Path(f"/sys/class/leds/{dev}/brightness")
        m_file = Path(f"/sys/class/leds/{dev}/max_brightness")
        if b_file.exists() and m_file.exists():
            max_val = int(m_file.read_text().strip())
            raw_val = round((percent / 100.0) * max_val)
            b_file.write_text(str(raw_val))
            return True, f"Keyboard backlight set to {percent}%"
    except PermissionError:
        return False, "Permission denied writing to keyboard backlight sysfs"
    except OSError as exc:
        return False, str(exc)

    return False, "No tool or permission to set keyboard backlight"
