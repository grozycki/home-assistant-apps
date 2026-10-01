import logging
from typing import Callable

from adb_shell.adb_device import AdbDevice
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult

logger = logging.getLogger("mcp_adb")


def register_app_tools(mcp: FastMCP, get_connected_device: Callable[[str], AdbDevice]) -> None:
    @mcp.tool()
    def list_installed_apps(device_uuid: str) -> ToolResult:
        """
        Retrieve a list of installed applications on the Android device.
        """

        adb_device: AdbDevice = get_connected_device(device_uuid)
        try:
            list_packages = adb_device.list_packages(filter_list=['-3'])
            count = len(list_packages)

            return ToolResult(
                structured_content={
                    "device_uuid": device_uuid,
                    "count": count,
                    "packages": list_packages
                }
            )

        except Exception as e:
            logger.error(f"Failed to list installed packages on device {device_uuid}: {e}")

            raise ToolError(f"Failed to list installed packages on device {device_uuid}")

    @mcp.tool()
    def get_current_app(device_uuid: str) -> ToolResult:
        """
        Retrieve the currently active application on the configured Android device.
        """
        adb_device: AdbDevice = get_connected_device(device_uuid)
        try:
            current_app = adb_device.app_current()
            return ToolResult(
                structured_content={
                    "device_uuid": device_uuid,
                    "package": current_app.package,
                    "activity": current_app.activity
                }
            )

        except Exception as e:
            logger.error(f"Error retrieving current app via ADB: {e}")

            raise ToolError(f"Failed to retrieve current app")
