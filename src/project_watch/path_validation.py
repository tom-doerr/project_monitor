"""Windows path validation and reserved name handling."""

import re
import sys
from pathlib import Path

_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
    "CLOCK$",
    "$Mft",
    "$MftMirr",
    "$LogFile",
    "$Volume",
    "$AttrDef",
    "$Bitmap",
    "$Boot",
    "$BadClus",
    "$Secure",
    "$Upcase",
    "$Extend",
    "$Quota",
    "$ObjId",
    "$Reparse",
}

_RESERVED_PATTERN = re.compile(
    r"^(CON|PRN|AUX|NUL|CLOCK\$|"
    r"COM[1-9]|LPT[1-9]|CONIN\$|CONOUT\$|"
    r"\$Mft|\$MftMirr|\$LogFile|\$Volume|"
    r"\$AttrDef|\$Bitmap|\$Boot|\$BadClus|"
    r"\$Secure|\$Upcase|\$Extend|"
    r"\$Quota|\$ObjId|\$Reparse)(\..*)?$",
    flags=re.IGNORECASE
)


def is_windows_reserved_path(path: Path) -> bool:
    """Check if path contains Windows reserved names in any component.
    Handles case-insensitive matching and Unicode normalization."""
    if sys.platform != "win32":
        return False

    try:
        return any(_RESERVED_PATTERN.match(part) for part in path.resolve().parts)
    except OSError:
        return False
