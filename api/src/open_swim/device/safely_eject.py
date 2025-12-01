
import os
import sys

import ctypes
from ctypes import wintypes

def safely_eject_device(mount_point: str) -> bool:
    r"""
    Attempt to safely eject a USB mass storage device.

    On Windows, uses DeviceIoControl(IOCTL_STORAGE_EJECT_MEDIA) against the
    volume handle (e.g., \\.:E:). On Linux/macOS, falls back to best-effort
    commands if available, else returns False.

    Returns True if the eject command was issued successfully, False otherwise.
    """
    try:
        if os.name == "nt":
            # Expect mount_point like "E:\\"; build \\.\E:
            drive_letter = mount_point.rstrip("\\/")
            if len(drive_letter) >= 2 and drive_letter[1] == ":":
                volume_path = f"\\\\.\\{drive_letter[:2]}"
            else:
                # Fallback: try first char + ':'
                volume_path = f"\\\\.\\{mount_point[:1]}:"

            GENERIC_READ = 0x80000000
            GENERIC_WRITE = 0x40000000
            FILE_SHARE_READ = 0x00000001
            FILE_SHARE_WRITE = 0x00000002
            OPEN_EXISTING = 3
            # IOCTL_STORAGE_EJECT_MEDIA
            IOCTL_STORAGE_EJECT_MEDIA = 0x2D4808

            CreateFileW = ctypes.windll.kernel32.CreateFileW
            CreateFileW.argtypes = [
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.HANDLE,
            ]
            CreateFileW.restype = wintypes.HANDLE

            DeviceIoControl = ctypes.windll.kernel32.DeviceIoControl
            DeviceIoControl.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
                ctypes.POINTER(wintypes.DWORD),
                wintypes.LPVOID,
            ]
            DeviceIoControl.restype = wintypes.BOOL

            CloseHandle = ctypes.windll.kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL

            handle = CreateFileW(
                volume_path,
                GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                0,
                None,
            )

            if handle == wintypes.HANDLE(-1).value:
                return False

            bytes_returned = wintypes.DWORD(0)
            ok = DeviceIoControl(
                handle,
                IOCTL_STORAGE_EJECT_MEDIA,
                None,
                0,
                None,
                0,
                ctypes.byref(bytes_returned),
                None,
            )
            CloseHandle(handle)
            return bool(ok)

        # Non-Windows best-effort
        if sys.platform.startswith("linux"):
            # Try udisksctl power-off to allow safe removal
            import subprocess
            try:
                subprocess.run(["sync"], check=False)
                # Users may pass /media/user/XYZ; can't infer block device easily here.
                # Try to unmount; actual power-off typically needs block path.
                subprocess.run(["udisksctl", "unmount", "-b", mount_point], check=False)
            except Exception:
                pass
            return False

        if sys.platform == "darwin":
            import subprocess
            try:
                subprocess.run(["sync"], check=False)
                subprocess.run(["diskutil", "unmount", mount_point], check=False)
            except Exception:
                pass
            return False

    except Exception:
        return False

    return False
