import threading
from logging import Logger
from typing import TypedDict, Optional

from zeroconf import Zeroconf, ServiceBrowser


class DiscoveredDevice(TypedDict):
    uuid: str
    ip: str
    friendly_name: str
    connect_port: Optional[int]
    pairing_port: Optional[int]


class ADBAutoDiscovery:
    """
    Hybrid mDNS Auto-Discovery for ADB-enabled Android TV / Google TV devices.
    Tracks devices permanently by their UUID, supporting dynamic IP changes,
    port rotations, and filtering out pure Chromecast devices.
    """

    def __init__(self, logger: Logger):
        self._service_types = [
            "_adb-tls-connect._tcp.local.",
            "_adb-tls-pairing._tcp.local.",
            "_googlecast._tcp.local."
        ]

        # Main dictionary keyed by permanent device UUID
        self._devices_by_uuid = {}

        # Helper map linking dynamic IP addresses to static UUIDs
        self._ip_to_uuid = {}

        self._lock = threading.Lock()
        self._zeroconf = None
        self._browsers = []
        self._is_running = False
        self._logger = logger

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

        packet_uuid = None
        friendly_name = None

        # Extract permanent Google Cast UUID ('id' TXT key) and Friendly Name ('fn' TXT key)
        if info.properties:
            id_bytes = info.properties.get(b'id')
            if id_bytes:
                try:
                    packet_uuid = id_bytes.decode('utf-8')
                except Exception:
                    pass

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
                existing_uuid_for_ip = self._ip_to_uuid.get(addr)
                target_uuid = None

                # Handle merging if temporary adb-host UUID was created before permanent Cast UUID arrived
                if packet_uuid:
                    target_uuid = packet_uuid
                    if existing_uuid_for_ip and existing_uuid_for_ip.startswith(
                            "adb-host-") and existing_uuid_for_ip != target_uuid:
                        temp_dev = self._devices_by_uuid.pop(existing_uuid_for_ip, None)
                        if temp_dev:
                            if target_uuid not in self._devices_by_uuid:
                                self._devices_by_uuid[target_uuid] = {
                                    "uuid": target_uuid,
                                    "ip": addr,
                                    "friendly_name": friendly_name,
                                    "connect_port": temp_dev.get("connect_port"),
                                    "pairing_port": temp_dev.get("pairing_port")
                                }
                            else:
                                if not self._devices_by_uuid[target_uuid]["connect_port"]:
                                    self._devices_by_uuid[target_uuid]["connect_port"] = temp_dev.get("connect_port")
                                if not self._devices_by_uuid[target_uuid]["pairing_port"]:
                                    self._devices_by_uuid[target_uuid]["pairing_port"] = temp_dev.get("pairing_port")
                elif existing_uuid_for_ip:
                    target_uuid = existing_uuid_for_ip
                else:
                    target_uuid = f"adb-host-{addr.replace('.', '-')}"

                # Update IP-to-UUID mapping
                self._ip_to_uuid[addr] = target_uuid

                # Initialize device entry if it doesn't exist yet
                if target_uuid not in self._devices_by_uuid:
                    self._devices_by_uuid[target_uuid] = {
                        "uuid": target_uuid,
                        "ip": addr,
                        "friendly_name": friendly_name,
                        "connect_port": None,
                        "pairing_port": None
                    }

                dev = self._devices_by_uuid[target_uuid]
                dev["ip"] = addr  # Update IP in case DHCP changed it
                dev["uuid"] = target_uuid

                # Update friendly name if Google Cast provided a clean user-facing name
                if friendly_name and not friendly_name.startswith("adb-") and "_googlecast" in type_:
                    dev["friendly_name"] = friendly_name
                elif not dev["friendly_name"] or dev["friendly_name"].startswith("adb-"):
                    if friendly_name and not friendly_name.startswith("adb-"):
                        dev["friendly_name"] = friendly_name

                # Assign appropriate ADB port
                if "_adb-tls-connect" in type_:
                    old_port = dev["connect_port"]
                    dev["connect_port"] = port
                    if old_port != port:
                        self._logger.info(f"[ADB Discovery] Device '{dev['friendly_name']}' ({addr}) -> connect port: {port}")
                elif "_adb-tls-pairing" in type_:
                    old_port = dev["pairing_port"]
                    dev["pairing_port"] = port
                    if old_port != port:
                        self._logger.info(f"[ADB Discovery] Device '{dev['friendly_name']}' ({addr}) -> pairing port: {port}")

    def start(self):
        """Starts background mDNS listeners."""
        if self._is_running:
            return

        def _run():
            self._zeroconf = Zeroconf()
            listener = self._MDNSListener(self)
            self._browsers = [ServiceBrowser(self._zeroconf, stype, listener) for stype in self._service_types]
            self._is_running = True
            self._logger.info("[ADB Discovery] Background mDNS listener started successfully.")

        threading.Thread(target=_run, daemon=True).start()

    def stop(self):
        """Stops background listeners and cleans up network resources."""
        if self._zeroconf and self._is_running:
            for browser in self._browsers:
                browser.cancel()
            self._zeroconf.close()
            self._is_running = False
            self._logger.info("[ADB Discovery] Background listener stopped.")

    def get_devices(self) -> dict[str, DiscoveredDevice]:
        """
        Returns a thread-safe copy of discovered ADB-enabled devices keyed by their UUID,
        including uuid, ip, friendly_name, connect_port, and pairing_port fields.
        """
        with self._lock:
            return {
                uuid: DiscoveredDevice(
                    uuid=data["uuid"],
                    ip=data["ip"],
                    friendly_name=data["friendly_name"],
                    connect_port=data["connect_port"],
                    pairing_port=data["pairing_port"],
                )
                for uuid, data in self._devices_by_uuid.items()
                if data["connect_port"] is not None or data["pairing_port"] is not None
            }

    def get_device_by_uuid(self, uuid: str) -> Optional[DiscoveredDevice]:
        """
        Returns a thread-safe copy of a specific discovered ADB-enabled device by its UUID.
        Returns None if the device is not found or has no active ADB ports.
        """
        with self._lock:
            data = self._devices_by_uuid.get(uuid)
            if data and (data["connect_port"] is not None or data["pairing_port"] is not None):
                return DiscoveredDevice(**data)
            return None
