import logging
import sys

from fastmcp import FastMCP

from adb_discovery import ADBAutoDiscovery
from app_tools import register_app_tools
from device_manager import DeviceManager
from pairing_tools import register_pairing_tools
from remote_tools import register_remote_tools

MDNS_PAIRING_SERVICE = "_adb-tls-pairing._tcp.local."
MDNS_CONNECT_SERVICE = "_adb-tls-connect._tcp.local."
MDNS_ADB_SERVICE = "_adb._tcp.local."

mcp = FastMCP("Android Debug Bridge")

adb_discovery = ADBAutoDiscovery()
adb_discovery.start()

device_manager = DeviceManager(adb_discovery=adb_discovery)

logger = logging.getLogger("mcp_adb")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

register_remote_tools(mcp=mcp, device_manager=device_manager)
register_app_tools(mcp=mcp, device_manager=device_manager)
register_pairing_tools(mcp=mcp, adb_discovery=adb_discovery)

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8555)
