from __future__ import annotations
import time
from typing import Iterable, List

from core.dongle import GlitchDongle
from utils.helpers import is_valid_hex, normalize_hex


class PacketInjector:
    """Transmit and replay packets over the ESP32 dongle."""

    def __init__(self, dongle: GlitchDongle) -> None:
        self.dongle = dongle

    def transmit(self, payload: str, timeout: float = 3.0) -> str:
        normalized = normalize_hex(payload)
        if not is_valid_hex(normalized):
            raise ValueError("Payload must be valid hexadecimal.")
        response = self.dongle.send_command(f"TX:{normalized}", wait_for="OK:TX_SUCCESS", timeout=timeout)
        return response or "OK:TX_SUCCESS"

    def replay_single(self, payload: str, count: int = 1, interval: float = 0.1) -> List[str]:
        responses: List[str] = []
        for _ in range(max(1, count)):
            responses.append(self.transmit(payload))
            time.sleep(interval)
        return responses

    def replay_all(self, packets: Iterable[dict], count: int = 1, interval: float = 0.1) -> List[str]:
        responses: List[str] = []
        for _ in range(max(1, count)):
            for packet in packets:
                if not packet or "hex" not in packet:
                    continue
                responses.append(self.transmit(packet["hex"]))
                time.sleep(interval)
        return responses

    def replay_loop(self, packets: Iterable[dict], interval: float = 0.2) -> None:
        while True:
            for packet in packets:
                if not packet or "hex" not in packet:
                    continue
                self.transmit(packet["hex"])
                time.sleep(interval)
