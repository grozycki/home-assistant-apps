import os
import sys
import logging
from fastmcp import FastMCP
from zeroconf import ServiceBrowser, Zeroconf
import time
from adbutils import adb, AdbDevice
from adbutils.errors import AdbError
import subprocess
from fastmcp.exceptions import ToolError

MDNS_PAIRING_SERVICE = "_adb-tls-pairing._tcp.local."
MDNS_CONNECT_SERVICE = "_adb-tls-connect._tcp.local."
MDNS_ADB_SERVICE = "_adb._tcp.local."

# Read configuration from environment variables with fallback defaults
DEVICE_IP = os.getenv("DEVICE_IP", "127.0.0.1")
# Handle potential empty string values from environment variables
port_env = os.getenv("PORT")
PORT = int(port_env) if port_env and port_env.isdigit() else 5555

mcp = FastMCP("Android Debug Bridge")

logger = logging.getLogger("mcp_adb")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


class ADBPortListener:
    """Listener capturing dynamic ADB port via mDNS."""

    def __init__(self, target_ip: str):
        self.target_ip = target_ip
        self.discovered_port = None

    def remove_service(self, zeroconf, type, name):
        pass

    def update_service(self, zeroconf, type, name):
        """Mandatory for newer zeroconf versions."""
        self.add_service(zeroconf, type, name)

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            parsed_ips = info.parsed_addresses()

            if self.target_ip in parsed_ips:
                self.discovered_port = info.port
                logger.info(f"mDNS: Discovered ADB port {info.port} for IP {self.target_ip} (Service: {name})")


def discover_connect_port(device_ip: str, timeout: int = 15, fallback_port: int = PORT) -> int:
    zeroconf = Zeroconf()
    listener = ADBPortListener(device_ip)

    logger.info(f"mDNS: Browsing for ADB connect port on {device_ip}...")
    browser = ServiceBrowser(zc=zeroconf, type_=MDNS_CONNECT_SERVICE, listener=listener)

    start_time = time.time()
    while time.time() - start_time < timeout:
        if listener.discovered_port:
            break
        time.sleep(0.1)

    zeroconf.close()

    if listener.discovered_port:
        logger.info(f"mDNS: Successfully discovered ADB port {listener.discovered_port} for {device_ip}.")
        return listener.discovered_port

    logger.warning(f"mDNS: Could not discover port for {device_ip}, falling back to {fallback_port}.")
    return fallback_port


def discover_pairing_port(device_ip: str, timeout: int = 15) -> int:
    zeroconf = Zeroconf()
    listener = ADBPortListener(device_ip)

    logger.info(f"mDNS: Browsing for ADB pairing port on {device_ip}...")
    browser = ServiceBrowser(zc=zeroconf, type_=MDNS_PAIRING_SERVICE, listener=listener)

    start_time = time.time()
    while time.time() - start_time < timeout:
        if listener.discovered_port:
            break
        time.sleep(0.1)

    zeroconf.close()

    if listener.discovered_port:
        logger.info(f"mDNS: Successfully discovered ADB port {listener.discovered_port} for {device_ip}.")
        return listener.discovered_port

    raise DeviceNotInPairingMode(f"Device {device_ip} is not in pairing mode. Please ensure the device is ready for pairing.")


class UnpairedDevice(Exception):
    pass

class DeviceNotInPairingMode(Exception):
    pass

def get_connected_device(device_ip: str = DEVICE_IP) -> AdbDevice:
    port = discover_connect_port(device_ip=device_ip)
    logger.info(f"Attempting to connect to {device_ip}:{port}...")
    target = f"{device_ip}:{port}"

    try:
        result = adb.connect(addr=target, timeout=10)
    except TimeoutError as e:
        logger.error(f"Failed to connect to {target}: {e}")
        raise RuntimeError(f"Failed to connect to {target}: {e}")

    logger.info(f"Connection result: {result}.")

    try:
        return adb.device(serial=target)
    except AdbError as e:
        logger.error(f"Failed to get device for {target}: {e}")

        if ("Can't find any android device/emulator" in str(e)
                or f"device '{target}' not found" in str(e)):
            raise UnpairedDevice(
                f"Device {device_ip} is not paired. Please pair the device first using the pairing code.")

        raise RuntimeError(f"Failed to get device for {target}: {e}")

@mcp.tool()
def run_app(package_name: str, media_uri: str = "") -> str:
    """
    Run an application on the configured Android device.
    If a media_uri (deep link) is provided, it attempts to launch directly into the specific content.

    Args:
        package_name: The package name of the application (e.g., 'com.netflix.ninja')
        media_uri: Optional deep link or URI to specific content (e.g., Netflix title URL or YouTube video link)
    """
    try:
        device = get_connected_device()

        if media_uri:
            # Force stop the app first to clear background state
            logger.info(f"Force stopping {package_name} to ensure clean launch...")
            device.shell(f"am force-stop {package_name}")

            # Convert web URL to Netflix internal URI scheme if applicable,
            # or pass the explicit intent with component structure
            if "netflix.com/title/" in media_uri:
                title_id = media_uri.split("/title/")[-1].split("/")[0]
                # Netflix internal URI scheme for Android TV
                nflx_uri = f"nflx://www.netflix.com/title/{title_id}"
                command = f"am start -a android.intent.action.VIEW -d '{nflx_uri}' {package_name}"
            else:
                command = f"am start -a android.intent.action.VIEW -d '{media_uri}' {package_name}"

            logger.info(f"Launching app with deep link: {command}")
        else:
            command = f"am start -n {package_name}/.MainActivity || monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
            logger.info(f"Launching app standard way: {command}")

        result = device.shell(command)

        return f"Successfully launched {package_name} on {DEVICE_IP}. Output: {result}"

    except Exception as e:
        logger.error(f"Error starting app via ADB: {e}")

        raise ToolError(f"Error starting app via ADB: {e}")


@mcp.tool()
def get_device_status() -> str:
    """
    Retrieve comprehensive status of the configured Android device, including power state,
    active foreground application, window focus, media session details (title, progress), and volume level.
    """
    try:
        device = get_connected_device()

        # 1. Fetch power and screen wakefulness state
        power_output = device.shell("dumpsys power | grep 'mWakefulness='")

        # 2. Fetch current active application on the foreground
        app_output = device.shell("dumpsys activity activities | grep mResumedActivity")

        # 3. Fetch window focus details (useful for app context)
        window_output = device.shell("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")

        # 4. Fetch active media session details (titles, playback state, position)
        media_output = device.shell("dumpsys media_session")

        # 5. Fetch simplified volume info safely
        audio_output = device.shell("dumpsys audio | grep -m 5 'Volume'")

        # Truncate long outputs to keep context clean for the AI model
        media_trimmed = media_output[:1500] if len(media_output) > 1500 else media_output
        audio_trimmed = audio_output[:1000] if len(audio_output) > 1000 else audio_output

        return (
            f"=== POWER STATE ===\n{power_output.strip()}\n\n"
            f"=== FOREGROUND APP ===\n{app_output.strip()}\n\n"
            f"=== WINDOW FOCUS ===\n{window_output.strip()}\n\n"
            f"=== AUDIO / VOLUME ===\n{audio_trimmed.strip()}\n\n"
            f"=== MEDIA SESSIONS ===\n{media_trimmed.strip()}"
        )

    except Exception as e:
        logger.error(f"Error fetching device status: {e}")

        raise ToolError(f"{e}")


@mcp.tool()
def list_installed_apps(device_ip: str = DEVICE_IP) -> dict:
    """
    Retrieve a list of installed applications on the Android device.
    """
    try:
        device = get_connected_device(device_ip=device_ip)
    except Exception as e:
        logger.error(f"Error connecting to device {device_ip}: {e}")
        raise ToolError(f"Error connecting to device {device_ip}: {e}")

    try:
        # -3 flag filters out system apps and shows only third-party (user) installed apps
        command = f"pm list packages -3"

        logger.info(f"Fetching installed apps with command: {command}")
        result = device.shell(command)

        cleaned_apps = [
            line.replace("package:", "").strip()
            for line in result.splitlines()
            if line.strip()
        ]

        return {
            "count": len(cleaned_apps),
            "apps": cleaned_apps,
        }

    except Exception as e:
        logger.error(f"Error listing installed apps: {e}")

        raise ToolError(f"{e}")


@mcp.tool()
def pair_device(pairing_code: str, device_ip: str = DEVICE_IP) -> bool:
    """
    Pair the Android device with the ADB server using the provided pairing code.

    Args:
        pairing_code: The pairing code for the device.
        device_ip: The IP address of the device to pair.

    Returns:
        True if pairing is successful, False otherwise.
    """
    pairing_port = discover_pairing_port(device_ip=device_ip)
    target = f"{device_ip}:{pairing_port}"
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

    return True


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8555)
