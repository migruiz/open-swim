import os
import subprocess


def mount_volume(device_path: str, mount_point: str) -> bool:
    """Mount the given device at mount_point."""
    os.makedirs(mount_point, exist_ok=True)
    result = subprocess.run(
        ["mount", device_path, mount_point],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"[INFO] Successfully mounted {device_path} at {mount_point}")
        return True

    print(f"[ERROR] Failed to mount {device_path}: {result.stderr}")
    return False


def unmount_volume(mount_point: str, lazy_fallback: bool = False) -> bool:
    """Unmount the given mount_point. Returns True if it is no longer mounted.

    lazy_fallback detaches a busy mount (umount -l); use it only when the device
    is already gone, where a clean unmount can no longer succeed.
    """
    result = subprocess.run(
        ["umount", mount_point],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"[INFO] Successfully unmounted {mount_point}")
        return True

    print(f"[WARN] Unmount failed for {mount_point}: {result.stderr}")
    if lazy_fallback:
        lazy = subprocess.run(
            ["umount", "-l", mount_point],
            capture_output=True,
            text=True,
        )
        if lazy.returncode == 0:
            print(f"[INFO] Lazily detached {mount_point}")
            return True
    return False
