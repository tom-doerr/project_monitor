"""Windows path validation and reserved name handling."""

import sys
from pathlib import Path

_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    "CLOCK$"
}

def is_windows_reserved_path(path: Path) -> bool:
    """Check if path contains Windows reserved names in any component.
    Handles case-insensitive matching.

    Returns:
        bool: True if path contains reserved components, False otherwise
    """
    is_reserved = False
    if sys.platform == "win32":
        try:
            is_reserved = any(
                part.split('.')[0].upper() in _WINDOWS_RESERVED_NAMES
                for part in path.parts
                if part
            )
        except OSError:
            is_reserved = True  # Assume reserved on error for safety
    return is_reserved
