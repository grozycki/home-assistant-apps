import time
from logging import Logger

from adbutils import AdbDevice
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult

from device_manager import DeviceManager


def register_app_tools(mcp: FastMCP, device_manager: DeviceManager, logger: Logger) -> None:
    @mcp.tool()
    def start_media_uri(device_uuid: str, package_name: str, media_uri: str) -> ToolResult:
        """
        Start a media URI (deep link) on the configured Android device.
        This function is intended to be used internally by app_start when a media_uri is provided.
        """
        adb_device: AdbDevice = device_manager.get_connected_device(device_uuid=device_uuid)

        _ensure_screen_on(adb_device=adb_device)

        try:
            logger.info(f"Starting media URI via ADB: {media_uri} on device {device_uuid}...")
            adb_device.app_start(package_name=package_name, activity=f"android.intent.action.VIEW -d '{media_uri}'")

            return ToolResult(
                structured_content={
                    "device_uuid": device_uuid,
                    "package_name": package_name,
                    "media_uri": media_uri
                })

        except Exception as e:
            logger.error(f"Error starting media URI via ADB: {e}")

            raise ToolError(f"Failed to start media URI {media_uri} for {package_name}")

    @mcp.tool()
    def list_installed_apps(device_uuid: str) -> ToolResult:
        """
        Retrieve a list of installed applications on the Android device.
        """

        adb_device: AdbDevice = device_manager.get_connected_device(device_uuid)
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
        adb_device: AdbDevice = device_manager.get_connected_device(device_uuid)
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

        Args:
            package_name: The package name of the application (e.g., 'com.disney.disneyplus')
            device_uuid: The UUID of the device to run the application on
        """

        adb_device: AdbDevice = device_manager.get_connected_device(device_uuid)

        _ensure_screen_on(adb_device=adb_device)

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

    @mcp.tool()
    def stop_app(device_uuid: str, package_name: str) -> ToolResult:
        """
        Stop a running application on the configured Android device.
        """
        adb_device: AdbDevice = device_manager.get_connected_device(device_uuid=device_uuid)
        try:
            logger.info(f"Stopping app via ADB: {package_name} on device {device_uuid}...")
            adb_device.app_stop(package_name=package_name)

            return ToolResult(
                structured_content={
                    "device_uuid": device_uuid,
                    "package_name": package_name,
                }
            )

        except Exception as e:
            logger.error(f"Error stopping app via ADB: {e}")

            raise ToolError(f"Failed to stop {package_name}")

    def _ensure_screen_on(adb_device: AdbDevice, timeout: int = 10) -> None:
        """Checks if the Android TV screen is awake, and wakes it up if it's sleeping."""
        try:

            if adb_device.is_screen_on():
                logger.debug("Screen is already awake.")
                return

            logger.debug("Screen is currently off/sleeping. Sending WAKEUP signal...")
            adb_device.keyevent("KEYCODE_WAKEUP")
            start_time = time.time()
            while time.time() - start_time < timeout:
                time.sleep(0.5)
                try:
                    if adb_device.is_screen_on():
                        logger.info("Screen successfully turned on.")
                        return
                except Exception:
                    pass

            logger.warning(f"Timeout reached ({timeout}s) waiting for screen to turn on. Proceeding anyway...")

        except Exception as e:
            logger.warning(f"Could not verify or ensure screen state: {e}. Proceeding anyway...")
