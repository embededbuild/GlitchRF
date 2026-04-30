from __future__ import annotations
import threading
from typing import Dict, List

from core.dongle import GlitchDongle


class SpectrumScanner:
    """Sweep 2.4 GHz channels and collect RSSI reports from the ESP32 dongle."""

    def __init__(self, dongle: GlitchDongle) -> None:
        self.dongle = dongle
        self.results: List[Dict[str, int]] = []
        self._lock = threading.Lock()

    def start_scan(self, timeout: float = 20.0) -> List[Dict[str, int]]:
        self.results = []

        def scan_handler(line: str) -> None:
            if line == "SCAN:END":
                return
            parts = line.split(":")
            if len(parts) < 5 or parts[0] != "SCAN" or parts[1] != "CH" or parts[3] != "RSSI":
                return
            try:
                channel = int(parts[2])
                rssi = int(parts[4])
            except ValueError:
                return
            with self._lock:
                self.results.append(
                    {
                        "channel": channel,
                        "frequency_mhz": self.channel_to_frequency(channel),
                        "rssi": rssi,
                    }
                )

        self.dongle.register_handler("SCAN:", scan_handler)
        try:
            self.dongle.send_command("SCAN_START", wait_for="SCAN:END", timeout=timeout)
        finally:
            self.dongle.unregister_handler("SCAN:", scan_handler)

        return sorted(self.results, key=lambda item: item["channel"])

    @staticmethod
    def channel_to_frequency(channel: int) -> float:
        return 2400.0 + float(channel)
