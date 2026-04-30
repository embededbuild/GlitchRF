from __future__ import annotations
from typing import Callable, Dict, List

from core.dongle import GlitchDongle

PacketCallback = Callable[[Dict[str, object]], None]


class PacketSniffer:
    """Capture packets from the ESP32 in promiscuous sniff mode."""

    def __init__(self, dongle: GlitchDongle, buffer_limit: int = 500) -> None:
        self.dongle = dongle
        self.buffer_limit = buffer_limit
        self.buffer: List[Dict[str, object]] = []
        self.callbacks: List[PacketCallback] = []
        self.stats: Dict[str, int] = {"packets": 0, "high_rssi": 0, "low_rssi": 0}
        self._active = False

    def _packet_handler(self, line: str) -> None:
        if not line.startswith("PKT:"):
            return
        parts = line.split(":")
        if len(parts) < 6:
            return
        try:
            hex_payload = parts[1]
            length = int(parts[3])
            rssi = parts[5]
        except (ValueError, IndexError):
            return
        packet = {"hex": hex_payload, "len": length, "rssi": rssi}
        self.buffer.append(packet)
        if len(self.buffer) > self.buffer_limit:
            self.buffer.pop(0)
        self.stats["packets"] += 1
        if rssi.upper() == "HIGH":
            self.stats["high_rssi"] += 1
        else:
            self.stats["low_rssi"] += 1
        for callback in list(self.callbacks):
            try:
                callback(packet)
            except Exception:
                continue

    def register_callback(self, callback: PacketCallback) -> None:
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def unregister_callback(self, callback: PacketCallback) -> None:
        self.callbacks = [cb for cb in self.callbacks if cb != callback]

    def clear_buffer(self) -> None:
        self.buffer.clear()
        self.stats = {"packets": 0, "high_rssi": 0, "low_rssi": 0}

    def start(self, timeout: float = 2.0) -> None:
        if self._active:
            return
        self.dongle.register_handler("PKT:", self._packet_handler)
        self.dongle.send_command("SNIFF_START", wait_for="SNIFF:START", timeout=timeout)
        self._active = True

    def stop(self, timeout: float = 2.0) -> None:
        if not self._active:
            return
        self.dongle.send_command("SNIFF_STOP", wait_for="SNIFF:STOP", timeout=timeout)
        self.dongle.unregister_handler("PKT:", self._packet_handler)
        self._active = False
