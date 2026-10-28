import os
import re
import shutil
import unicodedata
from typing import List

# Characters FAT never allows in a name, plus control characters.
_FAT_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def device_name(name: str) -> str:
    """Reduce a file or folder name to plain ASCII for the player.

    The Pi mounts the player's FAT disk with the kernel's default "ascii"
    character set, which rejects any other character with EINVAL. Accents are
    dropped ("Música" -> "Musica"), compatibility forms become their plain
    equivalent ("²" -> "2"), and anything else is removed.
    """
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return _FAT_INVALID.sub("", plain)


def copy_file_to_device(source: str, destination: str) -> None:
    """Copy one file to the player. On failure, remove any partial copy and re-raise."""
    try:
        shutil.copy2(source, destination)
    except Exception:
        try:
            if os.path.exists(destination):
                os.remove(destination)
        except OSError:
            pass
        raise


def copy_failures_message(prefix: str, failures: List[str], shown: int = 3) -> str:
    """Summarise failed copies for the sync progress error, listing the first few."""
    listed = "; ".join(failures[:shown])
    more = f" and {len(failures) - shown} more" if len(failures) > shown else ""
    return f"{prefix} Could not copy {len(failures)} file(s) to the device: {listed}{more}"
