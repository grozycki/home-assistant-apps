import xml.etree.ElementTree as ET
from logging import Logger

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult

from device_manager import DeviceManager


def register_system_tools(mcp: FastMCP, device_manager: DeviceManager, logger: Logger) -> None:
    @mcp.tool()
    def get_screen_texts(device_uuid: str) -> ToolResult:
        """
        Dumps the current UI hierarchy using adb_device.dump_hierarchy()
        and extracts all visible texts on the screen. Useful for inspecting
        screen contents and detecting profile selection screens.

        Args:
            device_uuid: UUID of the target device (required)
        """
        adb_device = device_manager.get_connected_device(device_uuid)

        try:
            logger.info(f"Dumping UI hierarchy via adb_device.dump_hierarchy() for {adb_device.serial}...")
            xml_data = adb_device.dump_hierarchy()

            root = ET.fromstring(xml_data)
            texts = []
            for node in root.iter('node'):
                text = node.get('text')
                desc = node.get('content-desc')

                if text and text.strip():
                    texts.append(text.strip())
                if desc and desc.strip() and desc != text:
                    texts.append(desc.strip())

            unique_texts = list(dict.fromkeys(texts))
            logger.info(f"Successfully extracted {len(unique_texts)} visible text elements from screen.")

            summary_text = f"Screen contains {len(unique_texts)} text elements: {', '.join(unique_texts[:15])}"
            if len(unique_texts) > 15:
                summary_text += "..."

            return ToolResult(
                content=summary_text,
                structured_content={
                    "status": "success",
                    "target": adb_device.serial,
                    "visible_texts": unique_texts
                }
            )

        except Exception as e:
            logger.error(f"Failed to dump hierarchy: {e}")
            raise ToolError(f"Failed to inspect screen via dump_hierarchy: {e}")
