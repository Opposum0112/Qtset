"""Unit tests for the safe external subprocess command adapter."""

from qtile_settings.adapters.commands import run_command


def test_empty_command_is_rejected():
    """Verify that attempting to execute an empty command argument list is rejected."""
    result = run_command([])
    assert not result.ok
    assert result.error == "No command specified"


def test_missing_command_is_reported():
    """Verify that invoking a non-existent binary is gracefully reported without throwing."""
    result = run_command(["qtile-settings-command-that-does-not-exist"])
    assert not result.ok
    assert "not found" in result.error
