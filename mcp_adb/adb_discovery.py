import time
import logging
import threading
import sys
from zeroconf import Zeroconf, ServiceBrowser

logger = logging.getLogger("mcp_adb")


class ADBAutoDiscovery:
    """
    Clean, decoupled mDNS Auto-Discovery for ADB-enabled Android TV / Google TV devices.
    Encapsulates all zeroconf listener contracts internally.
    """

    def __init__(self):
        self._service_types = [
            "_adb-tls-connect._tcp.local.",
            "_adb-tls-pairing._tcp.local.",
            "_googlecast._tcp.local."
        ]

        # Thread-safe dictionary storing discovered devices keyed by IP
        self._devices = {}
        self._lock = threading.Lock()

        # Internal networking states
        self._zeroconf = None
        self._browsers = []
        self._is_running = False

    class _MDNSListener:
        """
        Private internal listener fulfilling the zeroconf ServiceBrowser contract.
        Delegates incoming network events back to the parent ADBAutoDiscovery instance.
        """

        def __init__(self, parent_instance):
            self._parent = parent_instance

        def add_service(self, zc: Zeroconf, type_: str, name: str):
            self._parent._handle_service_event(zc, type_, name)

        def update_service(self, zc: Zeroconf, type_: str, name: str):
            self._parent._handle_service_event(zc, type_, name)

        def remove_service(self, zc: Zeroconf, type_: str, name: str):
            pass

    def _handle_service_event(self, zc: Zeroconf, type_: str, name: str):
        """Internal handler processing mDNS service data safely."""
        info = zc.get_service_info(type_, name)
        if not info:
            return

        addresses = info.parsed_addresses()
        port = info.port if "_googlecast" not in type_ else None

        # Extract friendly name from Google Cast TXT record ('fn' key) if available
        friendly_name = None
        if "_googlecast" in type_ and info.properties:
            fn_bytes = info.properties.get(b'fn')
            if fn_bytes:
                try:
                    friendly_name = fn_bytes.decode('utf-8')
                except Exception:
                    pass

        # Fallback to mDNS instance name if no Cast 'fn' is found
        if not friendly_name:
            friendly_name = name.split(".")[0]

        for addr in addresses:
            # Filter out IPv6 addresses
            if ":" in addr:
                continue

            with self._lock:
                if addr not in self._devices:
                    self._devices[addr] = {
                        "ip": addr,
                        "friendly_name": friendly_name,
                        "connect_port": None,
                        "pairing_port": None
                    }

                dev = self._devices[addr]

                # Update friendly name if Google Cast provided a clean user-facing name
                if friendly_name and not friendly_name.startswith("adb-") and "_googlecast" in type_:
                    dev["friendly_name"] = friendly_name
                elif not dev["friendly_name"] or dev["friendly_name"].startswith("adb-"):
                    if not friendly_name.startswith("adb-"):
                        dev["friendly_name"] = friendly_name

                # Assign appropriate ADB port
                if "_adb-tls-connect" in type_:
                    old_port = dev["connect_port"]
                    dev["connect_port"] = port
                    if old_port != port:
                        logger.info(f"[ADB Discovery] Device '{dev['friendly_name']}' ({addr}) -> connect port: {port}")
                elif "_adb-tls-pairing" in type_:
                    old_port = dev["pairing_port"]
                    dev["pairing_port"] = port
                    if old_port != port:
                        logger.info(f"[ADB Discovery] Device '{dev['friendly_name']}' ({addr}) -> pairing port: {port}")

    def start(self):
        """Starts background mDNS listeners."""
        if self._is_running:
            return

        def _run():
            self._zeroconf = Zeroconf()
            # Instantiate the internal listener, completely hiding zeroconf from the public interface
            listener = self._MDNSListener(self)
            self._browsers = [ServiceBrowser(self._zeroconf, stype, listener) for stype in self._service_types]
            self._is_running = True
            logger.info("[ADB Discovery] Background mDNS listener started successfully.")

        threading.Thread(target=_run, daemon=True).start()

    def stop(self):
        """Stops background listeners and cleans up network resources."""
        if self._zeroconf and self._is_running:
            for browser in self._browsers:
                browser.cancel()
            self._zeroconf.close()
            self._is_running = False
            logger.info("[ADB Discovery] Background listener stopped.")

    def get_devices(self) -> dict:
        """
        Returns a thread-safe copy of discovered devices that actually support ADB
        (i.e., have at least a connect or pairing port). Filters out pure Chromecasts.
        """
        with self._lock:
            return {
                ip: dict(data) for ip, data in self._devices.items()
                if data["connect_port"] is not None or data["pairing_port"] is not None
            }


if __name__ == "__main__":
    import signal

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stdout
    )

    print("--- RUNNING ENCAPSULATED ADB DISCOVERY TEST ---")
    print("Zeroconf implementation is fully hidden. Press Ctrl+C to stop.\n")

    discovery = ADBAutoDiscovery()
    discovery.start()


    def signal_handler(sig, frame):
        print("\nStopping discovery scanner...")
        discovery.stop()

        devices = discovery.get_devices()
        print(f"\nDiscovered ADB devices summary ({len(devices)}):")
        for ip, info in devices.items():
            print(
                f" - [{info['friendly_name']}] IP: {ip} | Connect: {info['connect_port']} | Pairing: {info['pairing_port']}")

        sys.exit(0)


    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
