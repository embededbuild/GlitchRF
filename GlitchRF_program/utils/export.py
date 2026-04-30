from __future__ import annotations
from datetime import datetime
from typing import Iterable, Mapping, Sequence


def export_packets(filepath: str, packets: Sequence[Mapping[str, object]]) -> None:
    with open(filepath, "w", encoding="utf-8") as file_handle:
        file_handle.write("# GlitchRF packet export\n")
        file_handle.write(f"# Generated: {datetime.now().isoformat()}\n")
        for index, packet in enumerate(packets, start=1):
            hex_payload = packet.get("hex", "")
            length = packet.get("len", "")
            rssi = packet.get("rssi", "")
            file_handle.write(f"{index}\t{hex_payload}\tLEN:{length}\tRSSI:{rssi}\n")


def export_scan_results(filepath: str, results: Iterable[Mapping[str, object]]) -> None:
    with open(filepath, "w", encoding="utf-8") as file_handle:
        file_handle.write("# GlitchRF scan export\n")
        file_handle.write(f"# Generated: {datetime.now().isoformat()}\n")
        for item in results:
            file_handle.write(
                f"CH:{item.get('channel')} FREQ:{item.get('frequency_mhz')} RSSI:{item.get('rssi')}\n"
            )
