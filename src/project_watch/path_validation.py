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
    r"^(CON|PRN|AUX|NUL|CLOCK\$|CONIN\$|CONOUT\$|FAX\$|"
    r"COM[0-9]|LPT[0-9]|"
    r"\$Mft|\$MftMirr|\$LogFile|\$Volume|"
    r"\$AttrDef|\$Bitmap|\$Boot|\$BadClus|"
    r"\$Secure|\$Upcase|\$Extend|"
    r"\$Quota|\$ObjId|\$Reparse)(\..*)?$",
    flags=re.IGNORECASE,
)


def is_windows_reserved_path(
    path: Path,
) -> bool:  # pylint: disable=too-many-return-statements
    """Check if path contains Windows reserved names in any component.
    Handles case-insensitive matching and Unicode normalization.

    Returns:
        bool: True if path contains reserved components, False otherwise
    """
    if sys.platform != "win32":
        return False

    try:
        normalized_path = path.resolve().as_posix().upper()

        # Check for reserved names with or without extensions
        if re.search(
            r"(^|/)(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]|CLOCK\$)(\..*)?(/|$)",
            normalized_path,
        ):
            return True

        # Check for NTFS special files
        if any(part.startswith("$") for part in path.parts):
            return True

        return False
    except OSError:
        return False
