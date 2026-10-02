import logging
import sys

from fastmcp import FastMCP

from adb_discovery import ADBAutoDiscovery
from app_tools import register_app_tools
from device_manager import DeviceManager
from pairing_tools import register_pairing_tools
from remote_tools import register_remote_tools
from system_tools import register_system_tools

logger = logging.getLogger("mcp_adb")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

mcp = FastMCP("Android Debug Bridge")

adb_discovery = ADBAutoDiscovery(logger=logger)
adb_discovery.start()

device_manager = DeviceManager(adb_discovery=adb_discovery, logger=logger)

register_remote_tools(mcp=mcp, device_manager=device_manager, logger=logger)
register_app_tools(mcp=mcp, device_manager=device_manager, logger=logger)
register_pairing_tools(mcp=mcp, adb_discovery=adb_discovery, logger=logger)
register_system_tools(mcp=mcp, device_manager=device_manager, logger=logger)

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8555)
