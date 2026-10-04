"""Audio adapter for PipeWire and WirePlumber audio management.

Interfaces with the system sound server via the `wpctl` CLI utility to inspect
master sink volumes, toggle mute states, and adjust output levels safely.
"""

from __future__ import annotations

from qtile_settings.adapters.commands import run_command


def get_volume() -> tuple[int | None, bool | None, str]:
    """Retrieve the current volume percentage and mute status of the default audio sink.

    Returns:
        A tuple of (volume_percent, is_muted, error_message).
        volume_percent: Integer between 0 and 150, or None if unavailable.
        is_muted: True if the sink is muted, False if unmuted, or None on error.
        error_message: Explanatory error string if the query failed, empty otherwise.
    """
    result = run_command(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    if not result.ok:
        return None, None, result.error

    # Typical wpctl output formats:
    # "Volume: 0.42" or "Volume: 0.42 [MUTED]"
    try:
        parts = result.stdout.split()
        volume = round(float(parts[1].strip("[]")) * 100)
        muted = "MUTED" in result.stdout
        # Clamp to valid range (0% to 150% with software amplification)
        return max(0, min(150, volume)), muted, ""
    except (IndexError, ValueError):
        return None, None, f"Unexpected wpctl output: {result.stdout}"


def set_volume(percent: int) -> tuple[bool, str]:
    """Set the default audio sink volume level.

    Args:
        percent: Target volume percentage, clamped safely between 0 and 150.

    Returns:
        A tuple of (success, error_message).
    """
    # Clamp requested percentage to safety limits
    percent = max(0, min(150, int(percent)))
    result = run_command(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent}%"])
    return result.ok, result.error


def set_muted(muted: bool) -> tuple[bool, str]:
    """Toggle or set the mute state of the default audio sink.

    Args:
        muted: True to mute audio output, False to unmute.

    Returns:
        A tuple of (success, error_message).
    """
    result = run_command(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if muted else "0"])
    return result.ok, result.error
