from logging import Logger

from adbutils import AdbDevice
from fastmcp.exceptions import ToolError

from adb_discovery import ADBAutoDiscovery, DiscoveredDevice


class DeviceManager:
    """
    Manages ADB connections and lifecycle, bridging mDNS auto-discovery
    with active ADB socket connections.
    """
    def __init__(self, adb_discovery: ADBAutoDiscovery, logger: Logger):
        self.adb_discovery = adb_discovery
        self.logger = logger

    def get_connected_device(self, device_uuid: str) -> AdbDevice:
        """
        Retrieve a connected ADB device handle based on the provided device UUID.
        Raises:
            ToolError: If the device is not found or cannot be connected.
        Returns:
            AdbDevice: A handle to the connected ADB device.
        """
        # 1. Flexible device lookup via discovery service
        discovered_device: DiscoveredDevice | None = self.adb_discovery.get_device_by_uuid(device_uuid)

        if not discovered_device:
            active_devices = self.adb_discovery.get_devices()
            available = [
                f"'{d['friendly_name']}' (UUID: {d['uuid']}, IP: {d['ip']})"
                for d in active_devices.values()
            ]
            raise ToolError(
                f"Device '{device_uuid}' not found. "
                f"Available devices: {', '.join(available) if available else 'None'}"
            )

        ip = discovered_device["ip"]
        connect_port = discovered_device["connect_port"]

        if not connect_port:
            raise ToolError(
                f"Device '{discovered_device['friendly_name']}' ({ip}) found, "
                f"but ADB connect port is unavailable. Ensure Wireless Debugging is active."
            )

        target = f"{ip}:{connect_port}"
        self.logger.info(f"Attempting to connect to {target}...")

        # 2. Execute ADB connect
        try:
            result = adb.connect(addr=target, timeout=10)
            self.logger.info(f"Connection result string: '{result}'")
        except Exception as e:
            self.logger.error(f"Failed to issue connect command to {target}: {e}")
            raise ToolError(f"Failed to connect to {target}: {e}")

        # 3. Check if ADB connect returned an error string instead of succeeding
        result_lower = str(result).lower()
        if "failed" in result_lower or "unable" in result_lower or "refused" in result_lower:
            raise ToolError(
                f"Device '{discovered_device['friendly_name']}' ({target}) refused connection. "
                f"It may require pairing first. ADB response: {result}"
            )

        # 4. Verify that the device is actually listed in active ADB devices
        connected_devices = adb.device_list()
        connected_serials = [d.serial for d in connected_devices]
        self.logger.debug(f"Active connected ADB serials: {connected_serials}")

        if target not in connected_serials and ip not in connected_serials:
            raise ToolError(
                f"Device '{discovered_device['friendly_name']}' ({target}) is not authorized or paired. "
                f"Please pair the device using the 6-digit code first."
            )

        # 5. Retrieve device handle safely
        try:
            adb_device: AdbDevice = adb.device(serial=target)

            if not adb_device:
                raise ToolError(
                    f"Device '{discovered_device['friendly_name']}' ({target}) is not available after connection.")

            return adb_device

        except Exception as e:
            raise ToolError(f"Failed to get device for {target}: {e}")
