import sys
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from open_swim.device.linux.monitor import LinuxDeviceMonitor
    from open_swim.device.windows.monitor import WindowsDeviceMonitor
    from open_swim.device.linux.monitor import DeviceConnectedCallback, DeviceDisconnectedCallback


def create_device_monitor(
    on_connected: "DeviceConnectedCallback",
    on_disconnected: "DeviceDisconnectedCallback"
) -> Union["LinuxDeviceMonitor", "WindowsDeviceMonitor"]:
    """
    Create a platform-specific device monitor.

    Args:
        on_connected: Callback when device connects (device_path, mount_point)
        on_disconnected: Callback when device disconnects

    Returns:
        WindowsDeviceMonitor on Windows, LinuxDeviceMonitor on other platforms
    """
    if sys.platform == "win32":
        from open_swim.device.windows.monitor import WindowsDeviceMonitor
        return WindowsDeviceMonitor(on_connected, on_disconnected)
    else:
        from open_swim.device.linux.monitor import LinuxDeviceMonitor
        return LinuxDeviceMonitor(on_connected, on_disconnected)


__all__ = ["create_device_monitor"]
