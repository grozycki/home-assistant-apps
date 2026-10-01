import logging
from typing import Callable

from adbutils import AdbDevice
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

    @mcp.tool()
    def launch_app(device_uuid: str, package_name: str) -> ToolResult:
        """
        Run an application on the configured Android device.
        If a media_uri (deep link) is provided, it attempts to launch directly into the specific content.

        Args:
            :param package_name: The package name of the application (e.g., 'com.disney.disneyplus')
            :param device_uuid: The UUID of the device to run the application on
        """

        adb_device: AdbDevice = get_connected_device(device_uuid)

        try:
            logger.info(f"Launching app via ADB: {package_name} on device {device_uuid}...")
            adb_device.app_start(package_name=package_name)

            return ToolResult(
                structured_content={
                    "device_uuid": device_uuid,
                    "package_name": package_name,
                })

        except Exception as e:
            logger.error(f"Error starting app via ADB: {e}")

            raise ToolError(f"Failed to launch {package_name}")