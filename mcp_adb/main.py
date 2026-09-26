import os
import sys
import logging
from fastmcp import FastMCP
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from zeroconf import ServiceBrowser, Zeroconf
import time

# Read configuration from environment variables with fallback defaults
DEVICE_IP = os.getenv("DEVICE_IP", "127.0.0.1")
# Handle potential empty string values from environment variables
port_env = os.getenv("PORT")
PORT = int(port_env) if port_env and port_env.isdigit() else 5555

mcp = FastMCP("Android Debug Bridge")


class ColoredFormatter(logging.Formatter):
    """Custom log formatter to add ANSI colors based on log level."""

    # ANSI color codes
    GREY = "\x1b[38;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    format_str = "%(asctime)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: GREY + format_str + RESET,
        logging.INFO: GREEN + format_str + RESET,
        logging.WARNING: YELLOW + format_str + RESET,
        logging.ERROR: RED + format_str + RESET,
        logging.CRITICAL: BOLD_RED + format_str + RESET
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.INFO])
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


logger = logging.getLogger("mcp_adb")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ColoredFormatter())


class ADBPortListener:
    """Listener to capture the dynamic ADB port via mDNS."""

    def __init__(self, target_ip: str):
        self.target_ip = target_ip
        self.discovered_port = None

    def remove_service(self, zeroconf, type, name):
        pass

    def update_service(self, zeroconf, type, name):
        """Required by newer zeroconf versions to handle service updates."""
        self.add_service(zeroconf, type, name)

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            addresses = [inf.decode('utf-8') if isinstance(inf, bytes) else str(inf) for inf in
                         info.addresses_as_string()]
            if self.target_ip in addresses or any(self.target_ip in str(addr) for addr in info.addresses):
                self.discovered_port = info.port
                logger.info(f"Discovered dynamic ADB port {info.port} for IP {self.target_ip}")


def discover_adb_port(target_ip: str, timeout: int = 5, fallback_port: int = 5555) -> int:
    """
    Scan local network using mDNS to find the dynamic wireless debugging port.
    """
    zeroconf = Zeroconf()
    listener = ADBPortListener(target_ip)

    # We listen for both standard ADB connection and pairing services
    service_types = [
        "_adb-tls-connect._tcp.local.",
        "_adb._tcp.local."
    ]

    logger.info(f"mDNS: Browsing network for ADB service on {target_ip}...")
    browser = ServiceBrowser(zeroconf, service_types, listener)

    start_time = time.time()
    while time.time() - start_time < timeout:
        if listener.discovered_port:
            break
        time.sleep(0.1)

    # Clean up zeroconf browser
    zeroconf.close()

    if listener.discovered_port:
        return listener.discovered_port

    logger.warning(f"Could not discover port via mDNS for {target_ip}, falling back to default {fallback_port}.")
    return fallback_port


def get_adb_signer(key_path: str = "/data/adbkey") -> PythonRSASigner:
    """Get or generate RSA keys required for ADB authorization."""
    os.makedirs(os.path.dirname(key_path), exist_ok=True)

    if not os.path.exists(key_path):
        logger.info("Generating new RSA keys for ADB...")
        keygen(key_path)

    with open(key_path) as f:
        priv = f.read()
    with open(key_path + '.pub') as f:
        pub = f.read()

    return PythonRSASigner(pub, priv)


def get_connected_device() -> AdbDeviceTcp:
    target_port = discover_adb_port(DEVICE_IP)

    device = AdbDeviceTcp(DEVICE_IP, target_port)
    signer = get_adb_signer()

    logger.info(f"Attempting to connect and authorize connection to {DEVICE_IP}:{target_port}...")
    device.connect(rsa_keys=[signer], auth_timeout_s=5)
    return device


@mcp.tool()
def check_connection_and_pair() -> str:
    """
    Test the connection to the Android device and verify RSA key authorization.
    If the device prompts for authorization, accept it on the physical screen.
    """
    try:
        device = get_connected_device()
        # Run a simple shell command to verify the session is fully authorized
        test_output = device.shell("echo 'Connection active'")
        device.close()

        return f"Successfully connected and authorized. Response: {test_output.strip()}"

    except Exception as e:
        logger.error(f"Authorization or connection failed: {e}")
        return (
            f"Failed to connect or authorize with {DEVICE_IP}. Error: {e}. "
            "Please check if the device is turned on, network debugging is enabled, "
            "and look at the physical screen of your Android device to accept the RSA key prompt."
        )


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
        device.close()

        return f"Successfully launched {package_name} on {DEVICE_IP}. Output: {result}"

    except Exception as e:
        logger.error(f"Error starting app via ADB: {e}")
        return f"Error starting app via ADB (Check authorization): {e}"


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

        device.close()

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
        return f"Error fetching device status (Check authorization): {e}"


@mcp.tool()
def list_installed_apps(third_party_only: bool = True) -> str:
    """
    Retrieve a list of installed applications on the Android device.

    Args:
        third_party_only: If True, lists only user-installed apps. If False, lists all packages.
    """
    try:
        device = get_connected_device()

        # -3 flag filters out system apps and shows only third-party (user) installed apps
        flag = "-3" if third_party_only else ""
        command = f"pm list packages {flag}"

        logger.info(f"Fetching installed apps with command: {command}")
        result = device.shell(command)
        device.close()

        # Clean up output format (remove 'package:' prefix for cleaner reading)
        cleaned_apps = "\n".join([line.replace("package:", "").strip() for line in result.splitlines() if line.strip()])

        return f"Installed Applications on {DEVICE_IP}:\n{cleaned_apps}"

    except Exception as e:
        logger.error(f"Error listing installed apps: {e}")
        return f"Error listing installed apps (Check authorization): {e}"


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8555)
