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


def unmount_volume(mount_point: str) -> bool:
    """Unmount the given mount_point."""
    result = subprocess.run(
        ["umount", mount_point],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"[INFO] Successfully unmounted {mount_point}")
        return True

    print(f"[WARN] Unmount warning for {mount_point}: {result.stderr}")
    return True  # treat as non-fatal
