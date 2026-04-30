# GlitchRF

> ESP32 + nRF24L01+ RF research tool for passive recon, packet capture, injection, and relay operations on the 2.4 GHz band.

---

## ⚠️ Legal Disclaimer

GlitchRF is intended for **authorized security research, penetration testing, and educational use only**. Intercepting, injecting, or replaying wireless transmissions without explicit permission from the network owner may violate local laws (e.g. CFAA, Computer Misuse Act, ETSI regulations). **You are solely responsible for how you use this tool.** Always obtain proper authorization before testing any wireless system.

---

## Overview

GlitchRF is a two-part RF research platform:

- **Firmware** (`GlitchRF.ino`) — flashed to an ESP32, drives the nRF24L01+ transceiver and exposes a simple serial command protocol over USB.
- **Controller** (`GlitchRF.py` + modules) — a Python CLI/interactive tool that communicates with the firmware over serial, providing spectrum scanning, packet sniffing, injection, replay, relay, and dual-dongle bridging.

---

## Hardware Requirements

| Component | Notes |
|-----------|-------|
| ESP32 dev board | Any standard ESP32 board works |
| nRF24L01+ module | PA+LNA version recommended for extended range |
| Jumper wires | Standard dupont wires |
| USB cable | For serial communication and power |

### Wiring

| nRF24L01+ Pin | ESP32 Pin |
|---------------|-----------|
| CE | GPIO 22 |
| CSN | GPIO 21 |
| SCK | GPIO 18 (SPI default) |
| MOSI | GPIO 23 (SPI default) |
| MISO | GPIO 19 (SPI default) |
| VCC | 3.3V |
| GND | GND |

---

## Firmware Setup

### Dependencies

Install via Arduino IDE Library Manager:

- [RF24](https://github.com/nRF24/RF24) by TMRh20

### Flashing

1. Open `GlitchRF.ino` in the Arduino IDE.
2. Select your ESP32 board under **Tools → Board**.
3. Select the correct COM port under **Tools → Port**.
4. Click **Upload** — no code modifications required.

On successful boot, the serial monitor (115200 baud) will print:

```
READY
```

---

## Python Controller Setup

### Requirements

- Python 3.8+
- [pyserial](https://pypi.org/project/pyserial/)
- *(Optional)* `matplotlib` and `numpy` — required for waterfall display

### Install

```bash
git clone https://github.com/yourname/GlitchRF.git
cd GlitchRF
pip install pyserial
# Optional: for waterfall visualization
pip install matplotlib numpy
```

### Project Structure

```
GlitchRF/
├── GlitchRF.ino          # ESP32 firmware
├── GlitchRF.py           # CLI entry point
├── core/
│   ├── dongle.py         # Serial communication & async dispatch
│   ├── radio.py          # Radio parameter control
│   └── scanner.py        # Spectrum sweep (SCAN_START)
├── ops/
│   ├── injector.py       # Packet TX and replay
│   ├── relay.py          # Transparent relay & dual-dongle bridge
│   └── sniffer.py        # Promiscuous packet capture
├── ui/
│   ├── menu.py           # Interactive terminal menu
│   └── waterfall.py      # Matplotlib waterfall display
└── utils/
    ├── export.py          # Packet buffer export
    └── helpers.py         # Input validation & hex utilities
```

---

## Usage

### CLI Mode

```bash
# Auto-detect device and launch interactive menu
python GlitchRF.py

# Specify a port explicitly
python GlitchRF.py --port /dev/ttyUSB0

# Run a spectrum scan
python GlitchRF.py --port /dev/ttyUSB0 --scan

# Sniff packets and export to file
python GlitchRF.py --port /dev/ttyUSB0 --sniff --export captures.txt

# Inject a raw hex payload
python GlitchRF.py --port /dev/ttyUSB0 --inject DEADBEEF

# Launch the interactive terminal menu
python GlitchRF.py --gui
```

### Interactive Menu

Once connected, the interactive menu provides access to all features:

```
Main menu:
 1) Configure radio
 2) Spectrum scan
 3) Packet sniff
 4) Inject packet
 5) Replay captured packets
 6) Transparent relay mode
 7) Bridge two dongles
 8) Export packet buffer
 9) Show waterfall
 0) Quit
```

---

## Features

### Spectrum Scan
Sweeps all 126 channels (2400–2525 MHz) using carrier detection and reports RSSI activity per channel. Supports optional waterfall visualization via matplotlib.

### Packet Sniffing (Promiscuous Mode)
Configures the nRF24L01+ with CRC disabled, auto-ack off, and a zero-byte address to capture raw packets from nearby 2.4 GHz devices. Captured packets include hex payload, length, and RSSI indicator.

### Packet Injection
Transmit arbitrary hex payloads over the air. Supports single transmissions, counted replay, and continuous replay loops.

### Transparent Relay Mode
Forwards all received packets to the host over serial in real time. Accepts `TX:<hex>` commands during relay to inject while listening. Exit with `RELAY_STOP`.

### Dual-Dongle Bridge
Bridges two connected ESP32 dongles — one listens, one retransmits — enabling man-in-the-middle style packet forwarding between two RF endpoints.

### Radio Configuration
All key radio parameters are runtime-configurable without reflashing:

| Parameter | Range | Default |
|-----------|-------|---------|
| Channel | 0–125 | 76 (2476 MHz) |
| TX Power | 0=MIN, 1=LOW, 2=HIGH, 3=MAX | MAX |
| Data Rate | 0=250kbps, 1=1Mbps, 2=2Mbps | 1Mbps |
| Pipe Address | Any 5-byte hex value | `0x0000000000` |

---

## Serial Command Protocol

The firmware communicates over serial at **115200 baud**. Commands are newline-terminated strings.

| Command | Response | Description |
|---------|----------|-------------|
| `PING` | `PONG:GlitchRF:V1.0` | Connectivity check |
| `SET_CHANNEL:<0-125>` | `OK:CHANNEL:<n>` | Set RF channel |
| `SET_POWER:<0-3>` | `OK:POWER:<n>` | Set PA level |
| `SET_RATE:<0-2>` | `OK:RATE:<n>` | Set data rate |
| `SET_ADDRESS:<hex>` | `OK:ADDRESS:<hex>` | Set pipe address |
| `SCAN_START` | `SCAN:CH:<n>:RSSI:<v>` × 126, then `SCAN:END` | Full spectrum sweep |
| `SNIFF_START` | `SNIFF:START`, then `PKT:<hex>:LEN:<n>:RSSI:<HIGH\|LOW>` | Begin packet capture |
| `SNIFF_STOP` | `SNIFF:STOP` | Stop packet capture |
| `TX:<hex>` | `OK:TX_SUCCESS` or `ERROR:TX_FAILED` | Transmit hex payload |
| `RELAY_START` | `RELAY:MODE_ACTIVE`, then `RELAY_FWD:<hex>` | Enter relay mode |
| `RELAY_STOP` | `RELAY:STOPPED` | Exit relay mode |

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Created by [embededbuild](https://github.com/embededbuild)*
