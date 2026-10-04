import time
from logging import Logger
from typing import Optional

from adbutils import AdbDevice
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult

from device_manager import DeviceManager


def register_app_tools(mcp: FastMCP, device_manager: DeviceManager, logger: Logger) -> None:
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
        adb_device: AdbDevice = device_manager.get_connected_device(device_uuid=device_uuid)
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
    def launch_app(device_uuid: str, package_name: str, deep_link: Optional[str] = None) -> ToolResult:
        """
        Run an application on the configured Android TV device.
        Automatically wakes up the screen if the TV is in standby mode.

        Args:
            package_name: The package name of the application (e.g., 'com.disney.disneyplus')
            device_uuid: The UUID of the device to run the application on
            deep_link: Optional deep-link URI to open specific video/audio content directly inside the app
        """

        _validate_app_launch_constraints(package_name, deep_link)

        adb_device: AdbDevice = device_manager.get_connected_device(device_uuid=device_uuid)

        _ensure_screen_on(adb_device=adb_device)

        try:
            if deep_link:
                logger.info(f"Launching app via ADB with deep link: {package_name} on device {device_uuid}...")
                # adb_device.app_start(package_name=package_name, activity=f"android.intent.action.VIEW -d '{deep_link}'")
                cmd = f"am start -a android.intent.action.VIEW -d '{deep_link}' -p {package_name}"
                output = adb_device.shell(cmd)
            else:
                logger.info(f"Launching app via ADB: {package_name} on device {device_uuid}...")
                output = adb_device.app_start(package_name=package_name)

            return ToolResult(
                structured_content={
                    "device_uuid": device_uuid,
                    "package_name": package_name,
                    "deep_link": deep_link,
                    "output": output.strip() if output else "OK",
                    "note": "If the app requires profile selection, use remote tools (like press_select or dpad navigation) to choose the profile."
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

    @mcp.tool()
    def trigger_global_search(device_uuid: str, query: str) -> ToolResult:
        """
        Triggers the Android TV global search intent with a custom query string.

        Args:
            device_uuid: UUID, friendly name, or IP of the target device
            query: The search text to pass to global search (e.g., 'Play Inception on Netflix')
        """
        adb_device = device_manager.get_connected_device(device_uuid)
        logger.info(f"Triggering global search with query: '{query}' on {adb_device.serial}")

        _ensure_screen_on(adb_device=adb_device)

        try:
            cmd = f"am start -a android.search.action.GLOBAL_SEARCH --es query '{query}'"
            output = adb_device.shell(cmd)

            return ToolResult(
                content=f"Successfully triggered global search with query: '{query}'",
                structured_content={
                    "status": "success",
                    "action": "global_search",
                    "query": query,
                    "output": output.strip() if output else "OK",
                    "hint": "If search results require confirmation, send input keyevent 66 (ENTER)."
                }
            )

        except Exception as e:
            logger.error(f"Failed to execute global search: {e}")
            raise ToolError(f"Failed to trigger global search")

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

    def _validate_app_launch_constraints(package_name: str, deep_link: Optional[str]) -> None:
        """
        Private validation helper to enforce application-specific workarounds
        and block unsupported parameters by raising actionable ToolErrors.
        """
        if package_name == "com.netflix.ninja" and deep_link:
            logger.warning("Attempted to use deep_link with Netflix - rejecting to enforce global search workaround.")
            raise ToolError(
                "Netflix (com.netflix.ninja) does not support direct deep links. "
                "The intent will be ignored by the Ninja engine. "
                "Please check the guide resource 'app://guide/com.netflix.ninja' "
            )
