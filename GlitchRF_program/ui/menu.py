from __future__ import annotations

import sys
from typing import Optional

from core.dongle import GlitchDongle
from core.radio import RadioConfig
from core.scanner import SpectrumScanner
from ops.injector import PacketInjector
from ops.relay import DongleBridge, RelayMode
from ops.sniffer import PacketSniffer
from ui.waterfall import WaterfallDisplay
from utils.export import export_packets
from utils.helpers import is_valid_hex, normalize_hex, safe_input


class InteractiveMenu:
    """Terminal-based interactive menu for GlitchRF operations."""

    def __init__(self, dongle: Optional[GlitchDongle] = None) -> None:
        self.dongle = dongle
        self.radio: Optional[RadioConfig] = None
        self.scanner: Optional[SpectrumScanner] = None
        self.sniffer: Optional[PacketSniffer] = None
        self.injector: Optional[PacketInjector] = None
        self.waterfall = WaterfallDisplay()

        if self.dongle is not None:
            self._bind_modules()

    def _bind_modules(self) -> None:
        if self.dongle is None:
            return
        self.radio = RadioConfig(self.dongle)
        self.scanner = SpectrumScanner(self.dongle)
        self.sniffer = PacketSniffer(self.dongle)
        self.injector = PacketInjector(self.dongle)

    def connect(self, port: Optional[str] = None) -> bool:
        if port is None and self.dongle is not None:
            return True
        try:
            if port:
                self.dongle = GlitchDongle(port)
            else:
                port = GlitchDongle.auto_detect()
                if port is None:
                    print("Could not auto-detect a GlitchRF dongle.")
                    return False
                self.dongle = GlitchDongle(port)
                print(f"Connected to {port}")
            self._bind_modules()
            return True
        except Exception as exc:
            print(f"Unable to connect: {exc}")
            return False

    def run(self) -> None:
        print("Welcome to GlitchRF interactive mode.")
        if self.dongle is None:
            self.connect()
        try:
            while True:
                print("\nMain menu:")
                print(" 1) Configure radio")
                print(" 2) Spectrum scan")
                print(" 3) Packet sniff")
                print(" 4) Inject packet")
                print(" 5) Replay captured packets")
                print(" 6) Transparent relay mode")
                print(" 7) Bridge two dongles")
                print(" 8) Export packet buffer")
                print(" 9) Show waterfall")
                print(" 0) Quit")
                choice = safe_input("Select an action: ").strip()
                if choice == "0":
                    break
                if choice == "1":
                    self.configure_radio()
                elif choice == "2":
                    self.perform_scan()
                elif choice == "3":
                    self.perform_sniff()
                elif choice == "4":
                    self.perform_inject()
                elif choice == "5":
                    self.perform_replay()
                elif choice == "6":
                    self.perform_relay()
                elif choice == "7":
                    self.perform_bridge()
                elif choice == "8":
                    self.perform_export()
                elif choice == "9":
                    self.perform_waterfall()
                else:
                    print("Please choose a valid option.")
        except KeyboardInterrupt:
            print("\nExiting interactive menu.")
        finally:
            if self.dongle is not None:
                self.dongle.close()

    def configure_radio(self) -> None:
        if self.radio is None and not self.connect():
            return
        try:
            channel_text = safe_input("Channel (0-125, blank to skip): ").strip()
            if channel_text:
                self.radio.set_channel(int(channel_text))
                print(f"Channel set to {channel_text}")
            power_text = safe_input("Power (0-3, blank to skip): ").strip()
            if power_text:
                self.radio.set_power(int(power_text))
                print(f"Power set to {power_text}")
            rate_text = safe_input("Rate (0=250kbps,1=1Mbps,2=2Mbps, blank to skip): ").strip()
            if rate_text:
                self.radio.set_rate(int(rate_text))
                print(f"Rate set to {rate_text}")
            address_text = safe_input("Address (hex, blank to skip): ").strip()
            if address_text:
                self.radio.set_address(address_text)
                print(f"Address set to {normalize_hex(address_text)}")
        except Exception as exc:
            print(f"Configuration error: {exc}")

    def perform_scan(self) -> None:
        if self.scanner is None and not self.connect():
            return
        try:
            print("Starting spectrum scan...")
            results = self.scanner.start_scan()
            print("Scan complete.")
            for item in results:
                print(f"CH {item['channel']:3d} | {item['frequency_mhz']:.1f} MHz | RSSI {item['rssi']}")
            self.waterfall.add_scan([item["rssi"] for item in results])
        except Exception as exc:
            print(f"Scan failed: {exc}")

    def perform_sniff(self) -> None:
        if self.sniffer is None and not self.connect():
            return
        self.sniffer.clear_buffer()

        def show_packet(packet: dict) -> None:
            print(f"PKT {packet['hex']} LEN {packet['len']} RSSI {packet['rssi']}")

        self.sniffer.register_callback(show_packet)
        try:
            print("Sniffer starting. Press Enter to stop.")
            self.sniffer.start()
            safe_input("")
        except KeyboardInterrupt:
            print("\nStopping sniff mode.")
        except Exception as exc:
            print(f"Sniffer error: {exc}")
        finally:
            self.sniffer.stop()
            self.sniffer.unregister_callback(show_packet)

    def perform_inject(self) -> None:
        if self.injector is None and not self.connect():
            return
        payload = safe_input("Hex payload to transmit: ").strip()
        if not payload:
            print("No payload entered.")
            return
        if not is_valid_hex(payload):
            print("Invalid hex payload.")
            return
        try:
            response = self.injector.transmit(payload)
            print(f"Inject response: {response}")
        except Exception as exc:
            print(f"Injection failed: {exc}")

    def perform_replay(self) -> None:
        if self.sniffer is None and not self.connect():
            return
        if not self.sniffer.buffer:
            print("No packets in sniff buffer. Capture packets first.")
            return
        count_text = safe_input("Replay count (default 1): ").strip() or "1"
        interval_text = safe_input("Interval seconds between packets (default 0.1): ").strip() or "0.1"
        try:
            count = int(count_text)
            interval = float(interval_text)
            responses = self.injector.replay_all(self.sniffer.buffer, count=count, interval=interval)
            print(f"Replayed {len(responses)} transmissions.")
        except Exception as exc:
            print(f"Replay failed: {exc}")

    def perform_relay(self) -> None:
        if self.dongle is None and not self.connect():
            return
        try:
            relay = RelayMode(self.dongle)
            relay.run_interactive()
        except Exception as exc:
            print(f"Relay failed: {exc}")

    def perform_bridge(self) -> None:
        if self.dongle is None:
            print("Connect a primary dongle first.")
            return
        second_port = safe_input("Second dongle port (blank to auto-detect): ").strip() or None
        try:
            second_dongle: Optional[GlitchDongle] = None
            if second_port:
                second_dongle = GlitchDongle(second_port)
            else:
                second_port = GlitchDongle.auto_detect()
                if second_port is None:
                    print("Could not auto-detect second dongle.")
                    return
                second_dongle = GlitchDongle(second_port)
            bridge = DongleBridge(receive_dongle=self.dongle, transmit_dongle=second_dongle)
            bridge.start()
            print("Bridge active. Press Enter to stop.")
            safe_input("")
            bridge.stop()
            second_dongle.close()
        except Exception as exc:
            print(f"Bridge failed: {exc}")

    def perform_export(self) -> None:
        if self.sniffer is None or not self.sniffer.buffer:
            print("No captured packets available to export.")
            return
        filename = safe_input("Export filename: ").strip()
        if not filename:
            print("Export cancelled.")
            return
        try:
            export_packets(filename, self.sniffer.buffer)
            print(f"Packets written to {filename}")
        except Exception as exc:
            print(f"Export error: {exc}")

    def perform_waterfall(self) -> None:
        if not self.waterfall.available:
            print("Matplotlib or NumPy not installed. Waterfall not available.")
            return
        if not self.waterfall.history:
            print("No waterfall data yet. Run a scan first.")
            return
        self.waterfall.render()
