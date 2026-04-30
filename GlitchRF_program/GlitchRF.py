#!/usr/bin/env python3
"""GlitchRF command-line controller for ESP32 + nRF24L01+ devices."""
from __future__ import annotations

import argparse
import sys

from core.dongle import GlitchDongle
from core.scanner import SpectrumScanner
from ops.injector import PacketInjector
from ops.sniffer import PacketSniffer
from ui.menu import InteractiveMenu
from ui.waterfall import WaterfallDisplay
from utils.helpers import safe_input


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GlitchRF serial controller for ESP32 + nRF24L01+ devices"
    )
    parser.add_argument("--port", "-p", help="Serial port for the ESP32 dongle")
    parser.add_argument("--scan", action="store_true", help="Run a spectrum scan and show results")
    parser.add_argument("--sniff", action="store_true", help="Start packet sniffing until stopped")
    parser.add_argument("--inject", metavar="HEX", help="Transmit a hex payload immediately")
    parser.add_argument("--export", metavar="FILE", help="Export any captured packets to a text file")
    parser.add_argument("--gui", action="store_true", help="Launch the interactive terminal menu")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.gui:
        try:
            InteractiveMenu().run()
        except KeyboardInterrupt:
            print("\nGoodbye from GlitchRF.")
        return 0

    port = args.port
    if not port:
        print("Auto-detecting GlitchRF device...")
        port = GlitchDongle.auto_detect()
        if not port:
            print("No GlitchRF device detected. Use --port to specify a serial port.")
            return 1
        print(f"Detected device on port {port}")

    try:
        with GlitchDongle(port) as dongle:
            if args.scan:
                scanner = SpectrumScanner(dongle)
                print("Starting spectrum scan...")
                results = scanner.start_scan()
                for item in results:
                    print(
                        f"CH {item['channel']:3d} | {item['frequency_mhz']:.1f} MHz | RSSI {item['rssi']}"
                    )
                if WaterfallDisplay().available:
                    display = WaterfallDisplay()
                    display.add_scan([item["rssi"] for item in results])
                    display.render()
                return 0

            if args.inject:
                injector = PacketInjector(dongle)
                print(f"Transmitting payload {args.inject}...")
                injector.transmit(args.inject)
                print("Transmission requested.")
                return 0

            if args.sniff:
                sniffer = PacketSniffer(dongle)
                print("Starting sniff mode. Press Enter to stop.")
                sniffer.clear_buffer()

                def show_packet(packet: dict) -> None:
                    print(
                        f"PKT {packet['hex']} LEN {packet['len']} RSSI {packet['rssi']}"
                    )

                sniffer.register_callback(show_packet)
                sniffer.start()
                try:
                    safe_input("Press Enter to stop sniffing... ")
                except KeyboardInterrupt:
                    print("\nStopping sniff mode.")
                finally:
                    sniffer.stop()
                if args.export:
                    from utils.export import export_packets

                    export_packets(args.export, sniffer.buffer)
                    print(f"Captured packets saved to {args.export}")
                return 0

            if args.export:
                print("No captured packet buffer available. Run --sniff before exporting.")
                return 1

            print("No action selected. Launching interactive menu.")
            InteractiveMenu(dongle).run()
            return 0
    except Exception as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
