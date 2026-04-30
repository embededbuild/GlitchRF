from __future__ import annotations
from typing import Callable, Optional

from core.dongle import GlitchDongle
from utils.helpers import is_valid_hex, normalize_hex

RelayNotify = Callable[[str], None]


class RelayMode:
    """Interactive transparent relay mode for the ESP32 dongle."""

    def __init__(self, dongle: GlitchDongle, notify: Optional[RelayNotify] = None) -> None:
        self.dongle = dongle
        self.notify = notify or (lambda message: print(message))
        self._active = False

    def _forward_handler(self, line: str) -> None:
        if not line.startswith("RELAY_FWD:"):
            return
        payload = line[len("RELAY_FWD:") :].strip()
        self.notify(f"Forwarded packet: {payload}")

    def start(self, timeout: float = 2.0) -> None:
        if self._active:
            return
        self.dongle.register_handler("RELAY_FWD:", self._forward_handler)
        self.dongle.send_command("RELAY_START", wait_for="RELAY:MODE_ACTIVE", timeout=timeout)
        self._active = True
        self.notify("Relay active. Type TX:<hex> to inject or RELAY_STOP to exit.")

    def stop(self, timeout: float = 2.0) -> None:
        if not self._active:
            return
        try:
            self.dongle.send_command("RELAY_STOP", wait_for="RELAY:STOP", timeout=timeout)
        except Exception:
            pass
        self.dongle.unregister_handler("RELAY_FWD:", self._forward_handler)
        self._active = False
        self.notify("Relay stopped.")

    def send_tx(self, payload: str) -> None:
        normalized = normalize_hex(payload)
        if not is_valid_hex(normalized):
            raise ValueError("Payload must be valid hexadecimal.")
        self.dongle.send_command(f"TX:{normalized}", wait_for=None, timeout=1.0)

    def run_interactive(self) -> None:
        self.start()
        try:
            while self._active:
                try:
                    command = input("relay> ").strip()
                except KeyboardInterrupt:
                    self.notify("\nKeyboard interrupt received, stopping relay.")
                    break
                if not command:
                    continue
                if command.upper() == "RELAY_STOP":
                    self.stop()
                    break
                if command.upper().startswith("TX:"):
                    self.send_tx(command[3:])
                else:
                    self.notify("Please type TX:<hex> to send or RELAY_STOP to quit.")
        finally:
            if self._active:
                self.stop()


class DongleBridge:
    """Bridge packets from one dongle receiver into a second transmitter dongle."""

    def __init__(self, receive_dongle: GlitchDongle, transmit_dongle: GlitchDongle) -> None:
        self.receive_dongle = receive_dongle
        self.transmit_dongle = transmit_dongle
        self._bridge_active = False

    def _packet_handler(self, line: str) -> None:
        if not line.startswith("PKT:"):
            return
        parts = line.split(":")
        if len(parts) < 6:
            return
        payload = parts[1]
        try:
            self.transmit_dongle.send_command(f"TX:{payload}", wait_for=None, timeout=1.0)
        except Exception:
            pass

    def start(self) -> None:
        if self._bridge_active:
            return
        self.receive_dongle.register_handler("PKT:", self._packet_handler)
        self.receive_dongle.send_command("SNIFF_START", wait_for="SNIFF:START", timeout=2.0)
        self._bridge_active = True

    def stop(self) -> None:
        if not self._bridge_active:
            return
        try:
            self.receive_dongle.send_command("SNIFF_STOP", wait_for="SNIFF:STOP", timeout=2.0)
        except Exception:
            pass
        self.receive_dongle.unregister_handler("PKT:", self._packet_handler)
        self._bridge_active = False
