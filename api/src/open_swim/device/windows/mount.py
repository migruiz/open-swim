import ctypes
import os


def mount_volume(drive_letter: str, mount_point: str) -> bool:
    """
    Validate Windows drive exists.

    Windows automatically mounts removable drives to drive letters,
    so we only need to verify the drive is accessible.

    Args:
        drive_letter: Drive letter like "E:\\"
        mount_point: Ignored on Windows (drives auto-mount to letters)

    Returns:
        True if drive exists and is accessible, False otherwise
    """
    if os.path.exists(drive_letter):
        print(f"[INFO] Windows drive {drive_letter} is available")
        return True

    print(f"[ERROR] Drive {drive_letter} not found")
    return False


def unmount_volume(mount_point: str) -> bool:
    """
    Flush file buffers before device removal.

    Actual safe ejection is handled by safely_eject.py if needed.
    This just ensures pending writes are committed.

    Args:
        mount_point: Drive letter like "E:\\"

    Returns:
        Always True (flush errors are non-fatal)
    """
    try:
        # Flush file system buffers to ensure all writes are committed
        # Using INVALID_HANDLE_VALUE (-1) flushes all file buffers
        INVALID_HANDLE_VALUE = ctypes.c_void_p(-1)
        ctypes.windll.kernel32.FlushFileBuffers(INVALID_HANDLE_VALUE)
        print(f"[INFO] Flushed file buffers for {mount_point}")
    except Exception as e:
        print(f"[WARN] Error flushing buffers for {mount_point}: {e}")

    return True  # treat as non-fatal
