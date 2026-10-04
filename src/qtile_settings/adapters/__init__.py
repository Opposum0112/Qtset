"""System and environment adapters for Qtile Settings.

Encapsulates all operating system queries, hardware controllers (audio, backlight,
touchpad), NetworkManager IPC, Qtile window manager IPC, file backups, and AST
configuration parsers. Keeps OS integration completely decoupled from UI presentation.
"""

from __future__ import annotations