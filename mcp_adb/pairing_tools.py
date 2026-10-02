import subprocess
from logging import Logger

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult

from adb_discovery import ADBAutoDiscovery


def register_pairing_tools(mcp: FastMCP, adb_discovery: ADBAutoDiscovery, logger: Logger) -> None:
    @mcp.tool()
    def list_discovered_devices() -> ToolResult:
        """
        Retrieve a list of discovered Android devices on the local network via mDNS.
        """
        try:
            return ToolResult(
                structured_content=adb_discovery.get_devices()
            )
        except Exception as e:
            logger.error(f"Error retrieving devices: {e}")

            raise ToolError(f"Failed to retrieve devices")

    @mcp.tool()
    def pair_device(pairing_code: str, device_uuid: str) -> ToolResult:
        """
        Pair the Android device with the ADB server using the provided pairing code.

        Args:
            pairing_code: The pairing code for the device.
            device_uuid: The UUID of the device to pair.

        Returns:
            ToolResult: The result of the pairing operation.
        """
        discovered_device = adb_discovery.get_device_by_uuid(device_uuid)
        if not discovered_device:
            raise ToolError(f"Device with UUID {device_uuid} is not found.")

        pairing_port = discovered_device["pairing_port"]
        if not pairing_port:
            raise ToolError(
                f"Device '{discovered_device['friendly_name']}' ({discovered_device['ip']}) does not have a pairing port available. Ensure Wireless Debugging is active.")
        target = f"{discovered_device['ip']}:{pairing_port}"
        logger.warning(f"Attempting to pair with {target} using code {pairing_code}...")
        res = subprocess.run(
            ["adb", "pair", target, str(pairing_code)],
            capture_output=True,
            text=True,
            timeout=10
        )

        if res.returncode != 0:
            raise ToolError(f"Failed to pair with {target}: {res.stderr.strip()}")

        logger.info(f"Successfully paired with {target}. Output: {res.stdout.strip()}")

        return ToolResult('Success')
