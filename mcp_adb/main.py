import os
import sys
import logging
from fastmcp import FastMCP
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner

# Read configuration from environment variables with fallback defaults
DEVICE_IP = os.getenv("DEVICE_IP", "127.0.0.1")
# Handle potential empty string values from environment variables
port_env = os.getenv("PORT")
PORT = int(port_env) if port_env and port_env.isdigit() else 5555

mcp = FastMCP("Android Debug Bridge")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mcp_adb")


def get_adb_signer(key_path: str = "/data/adbkey") -> PythonRSASigner:
    """Get or generate RSA keys required for ADB authorization."""
    os.makedirs(os.path.dirname(key_path), exist_ok=True)

    if not os.path.exists(key_path):
        logger.info("Generating new RSA keys for ADB...")
        keygen(key_path)

    with open(key_path, 'r') as f:
        priv = f.read()
    with open(key_path + '.pub', 'r') as f:
        pub = f.read()

    return PythonRSASigner(pub, priv)


@mcp.tool()
def check_connection_and_pair() -> str:
    """
    Test the connection to the Android device and verify RSA key authorization.
    If the device prompts for authorization, accept it on the physical screen.
    """
    try:
        device = AdbDeviceTcp(DEVICE_IP, PORT)
        signer = get_adb_signer()

        logger.info(f"Attempting to connect and authorize connection to {DEVICE_IP}:{PORT}...")
        # Try to connect with a short timeout
        device.connect(rsa_keys=[signer], auth_timeout_s=5)

        # Run a simple shell command to verify the session is fully authorized
        test_output = device.shell("echo 'Connection active'")
        device.close()

        return f"Successfully connected and authorized with {DEVICE_IP}:{PORT}. Response: {test_output.strip()}"

    except Exception as e:
        logger.error(f"Authorization or connection failed: {e}")
        return (
            f"Failed to connect or authorize with {DEVICE_IP}:{PORT}. Error: {e}. "
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
        device = AdbDeviceTcp(DEVICE_IP, PORT)
        signer = get_adb_signer()

        device.connect(rsa_keys=[signer], auth_timeout_s=5)

        if media_uri:
            # Launch with specific content URI (Deep Link) to bypass profile selection / home screen
            command = f"am start -a android.intent.action.VIEW -d '{media_uri}' {package_name}"
            logger.info(f"Launching app with media URI: {command}")
        else:
            # Fallback to standard launch intent if no URI is specified
            command = f"am start -n {package_name}/.MainActivity || monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
            logger.info(f"Launching app standard way: {command}")

        result = device.shell(command)
        device.close()

        return f"Successfully launched {package_name} on {DEVICE_IP}:{PORT}. Output: {result}"

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
        device = AdbDeviceTcp(DEVICE_IP, PORT)
        signer = get_adb_signer()

        device.connect(rsa_keys=[signer], auth_timeout_s=5)

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


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8555)