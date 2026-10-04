"""Subprocess execution adapter.

Executes external CLI binaries safely using argument vectors (argv) with strict timeouts,
path verification via shutil.which, error trapping, and zero shell evaluation (shell=False)
to prevent shell injection vulnerabilities.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    """Immutable result structure of an external process invocation.

    Attributes:
        ok: True if the process completed with returncode 0.
        stdout: Standard output stripped of trailing whitespace.
        error: Standard error or descriptive failure reason.
    """

    ok: bool
    stdout: str = ""
    error: str = ""


def run_command(argv: list[str], timeout: float = 3.0) -> CommandResult:
    """Run an executable with an argument list safely without invoking a shell.

    Args:
        argv: Command and arguments list (e.g. ["qtile", "check", "-c", "config.py"]).
        timeout: Maximum execution time in seconds before terminating.

    Returns:
        A CommandResult object containing execution status and captured text.
    """
    if not argv:
        return CommandResult(False, error="No command specified")

    # Ensure executable exists in current PATH before running
    if shutil.which(argv[0]) is None:
        return CommandResult(False, error=f"Required command not found: {argv[0]}")

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(False, error=f"Command timed out after {timeout}s: {argv[0]}")
    except OSError as exc:
        return CommandResult(False, error=f"OS execution error: {exc}")

    if result.returncode != 0:
        return CommandResult(
            False,
            stdout=result.stdout.strip(),
            error=result.stderr.strip() or f"Exit status {result.returncode}",
        )

    return CommandResult(True, stdout=result.stdout.strip())
