from __future__ import annotations

from typing import Optional

from core.dongle import GlitchDongle
from utils.helpers import is_valid_hex, normalize_hex


class RadioConfig:
    """Radio parameter control for the connected ESP32 dongle."""

    def __init__(self, dongle: GlitchDongle) -> None:
        self.dongle = dongle

    def set_channel(self, channel: int) -> str:
        if not 0 <= channel <= 125:
            raise ValueError("Channel must be between 0 and 125.")
        return self.dongle.send_command(f"SET_CHANNEL:{channel}", wait_for=f"OK:CHANNEL:{channel}", timeout=2.0)

    def set_power(self, level: int) -> str:
        if not 0 <= level <= 3:
            raise ValueError("Power level must be between 0 and 3.")
        return self.dongle.send_command(f"SET_POWER:{level}", wait_for=f"OK:POWER:{level}", timeout=2.0)

    def set_rate(self, rate: int) -> str:
        if not 0 <= rate <= 2:
            raise ValueError("Rate must be 0, 1, or 2.")
        return self.dongle.send_command(f"SET_RATE:{rate}", wait_for=f"OK:RATE:{rate}", timeout=2.0)

    def set_address(self, address: str) -> str:
        normalized = normalize_hex(address)
        if not is_valid_hex(normalized):
            raise ValueError("Address must be a valid hexadecimal string.")
        return self.dongle.send_command(
            f"SET_ADDRESS:{normalized}", wait_for=f"OK:ADDRESS:{normalized}", timeout=2.0
        )

    def ping(self, timeout: float = 2.0) -> Optional[str]:
        return self.dongle.ping(timeout=timeout)
