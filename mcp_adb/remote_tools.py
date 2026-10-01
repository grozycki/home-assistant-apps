import logging
from enum import Enum
from typing import Callable

from adbutils import AdbDevice
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult

logger = logging.getLogger("mcp_adb")


class GoogleTVKeycode(str, Enum):
    """Keycode string constants for standard Google TV white remote."""
    DPAD_UP = "KEYCODE_DPAD_UP"
    DPAD_DOWN = "KEYCODE_DPAD_DOWN"
    DPAD_LEFT = "KEYCODE_DPAD_LEFT"
    DPAD_RIGHT = "KEYCODE_DPAD_RIGHT"
    DPAD_CENTER = "KEYCODE_DPAD_CENTER"
    BACK = "KEYCODE_BACK"
    HOME = "KEYCODE_HOME"
    VOICE_ASSIST = "KEYCODE_VOICE_ASSIST"
    POWER = "KEYCODE_POWER"
    TV_POWER = "KEYCODE_TV_POWER"
    TV_INPUT = "KEYCODE_TV_INPUT"
    VOLUME_UP = "KEYCODE_VOLUME_UP"
    VOLUME_DOWN = "KEYCODE_VOLUME_DOWN"
    VOLUME_MUTE = "KEYCODE_VOLUME_MUTE"
    BUTTON_YOUTUBE = "KEYCODE_BUTTON_3"
    BUTTON_NETFLIX = "KEYCODE_BUTTON_4"
    MEDIA_PLAY_PAUSE = "KEYCODE_MEDIA_PLAY_PAUSE"
    MEDIA_STOP = "KEYCODE_MEDIA_STOP"
    MEDIA_NEXT = "KEYCODE_MEDIA_NEXT"
    MEDIA_PREVIOUS = "KEYCODE_MEDIA_PREVIOUS"
    MEDIA_FAST_FORWARD = "KEYCODE_MEDIA_FAST_FORWARD"
    MEDIA_REWIND = "KEYCODE_MEDIA_REWIND"


def register_remote_tools(mcp: FastMCP, get_connected_device: Callable[[str], AdbDevice]) -> None:
    """
    Registers all Google TV remote tools onto the provided FastMCP instance.

    Args:
        mcp: The active FastMCP server instance.
        get_connected_device: Function resolving device_uuid to a connected AdbDevice.
    """

    def _press_remote_button(button: GoogleTVKeycode, device_uuid: str) -> ToolResult:
        """
        Simulates pressing a physical button on the Google TV remote using textual KEYCODEs.

        Args:
            button: Keycode enum value (e.g., GoogleTVKeycode.DPAD_CENTER or "KEYCODE_DPAD_CENTER").
            device_uuid: Optional target device UUID, friendly name, or IP.
        """
        try:
            adb_device: AdbDevice = get_connected_device(device_uuid)
            adb_device.shell(f"input keyevent {button.value}")

            return ToolResult('Success')

        except Exception as e:
            logger.error(f"Error pressing button via ADB: {e}")

            raise ToolError(f"Failed to press button")

    # --- Navigation ---

    @mcp.tool()
    def press_dpad_up(device_uuid: str) -> ToolResult:
        """Simulate pressing the D-Pad Up button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.DPAD_UP, device_uuid=device_uuid)

    @mcp.tool()
    def press_dpad_down(device_uuid: str) -> ToolResult:
        """Simulate pressing the D-Pad Down button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.DPAD_DOWN, device_uuid=device_uuid)

    @mcp.tool()
    def press_dpad_left(device_uuid: str) -> ToolResult:
        """Simulate pressing the D-Pad Left button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.DPAD_LEFT, device_uuid=device_uuid)

    @mcp.tool()
    def press_dpad_right(device_uuid: str) -> ToolResult:
        """Simulate pressing the D-Pad Right button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.DPAD_RIGHT, device_uuid=device_uuid)

    @mcp.tool()
    def press_select(device_uuid: str) -> ToolResult:
        """Simulate pressing the Center/OK (Select) button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.DPAD_CENTER, device_uuid=device_uuid)

    # --- System Controls ---

    @mcp.tool()
    def press_back(device_uuid: str) -> ToolResult:
        """Simulate pressing the Back button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.BACK, device_uuid=device_uuid)

    @mcp.tool()
    def press_home(device_uuid: str) -> ToolResult:
        """Simulate pressing the Home button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.HOME, device_uuid=device_uuid)

    @mcp.tool()
    def press_power(device_uuid: str) -> ToolResult:
        """Simulate pressing the Power button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.POWER, device_uuid=device_uuid)

    # --- Volume Controls ---

    @mcp.tool()
    def press_volume_up(device_uuid: str) -> ToolResult:
        """Simulate pressing the Volume Up button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.VOLUME_UP, device_uuid=device_uuid)

    @mcp.tool()
    def press_volume_down(device_uuid: str) -> ToolResult:
        """Simulate pressing the Volume Down button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.VOLUME_DOWN, device_uuid=device_uuid)

    @mcp.tool()
    def press_volume_mute(device_uuid: str) -> ToolResult:
        """Simulate pressing the Volume Mute button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.VOLUME_MUTE, device_uuid=device_uuid)

    # --- Media Controls ---

    @mcp.tool()
    def press_play(device_uuid: str) -> ToolResult:
        """Simulate pressing the Play/Pause button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.MEDIA_PLAY_PAUSE, device_uuid=device_uuid)

    @mcp.tool()
    def press_stop(device_uuid: str) -> ToolResult:
        """Simulate pressing the Stop button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.MEDIA_STOP, device_uuid=device_uuid)

    @mcp.tool()
    def press_next(device_uuid: str) -> ToolResult:
        """Simulate pressing the Next track button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.MEDIA_NEXT, device_uuid=device_uuid)

    @mcp.tool()
    def press_previous(device_uuid: str) -> ToolResult:
        """Simulate pressing the Previous track button on the connected Android device."""
        return _press_remote_button(button=GoogleTVKeycode.MEDIA_PREVIOUS, device_uuid=device_uuid)
