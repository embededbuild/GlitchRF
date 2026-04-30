from __future__ import annotations

import queue
import threading
import time
from typing import Callable, Dict, List, Optional

import serial
import serial.tools.list_ports

ResponseHandler = Callable[[str], None]


class GlitchDongle:
    """Manage serial communication and dispatch asynchronous ESP32 responses."""

    def __init__(self, port: str, baud: int = 115200, timeout: float = 0.1, connect_delay: float = 0.3) -> None:
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.serial = serial.Serial(port, baudrate=baud, timeout=timeout)
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        self.handlers: Dict[str, List[ResponseHandler]] = {}
        self._response_queue: queue.Queue[str] = queue.Queue()
        self._reader_active = threading.Event()
        self._reader_active.set()
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name="GlitchDongleReader",
        )
        self._reader_thread.start()
        time.sleep(connect_delay)

    def register_handler(self, prefix: str, handler: ResponseHandler) -> None:
        if prefix not in self.handlers:
            self.handlers[prefix] = []
        self.handlers[prefix].append(handler)

    def unregister_handler(self, prefix: str, handler: ResponseHandler) -> None:
        if prefix in self.handlers:
            self.handlers[prefix] = [h for h in self.handlers[prefix] if h != handler]
            if not self.handlers[prefix]:
                del self.handlers[prefix]

    def send_command(self, command: str, wait_for: Optional[str] = None, timeout: float = 2.0) -> Optional[str]:
        text = command.strip()
        if not text:
            raise ValueError("Command cannot be empty.")
        self.serial.write((text + "\n").encode("utf-8"))
        self.serial.flush()
        if wait_for is None:
            return None

        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            try:
                line = self._response_queue.get(timeout=remaining)
            except queue.Empty:
                break
            if line.startswith(wait_for):
                return line
        raise TimeoutError(f"Timeout waiting for response that starts with {wait_for!r}")

    def ping(self, timeout: float = 2.0) -> Optional[str]:
        try:
            return self.send_command("PING", wait_for="PONG:", timeout=timeout)
        except TimeoutError:
            return None

    @staticmethod
    def list_ports() -> List[str]:
        return [port.device for port in serial.tools.list_ports.comports()]

    @classmethod
    def auto_detect(cls, timeout: float = 2.0) -> Optional[str]:
        for port in cls.list_ports():
            try:
                dongle = cls(port, timeout=0.2)
                response = dongle.ping(timeout=timeout)
                dongle.close()
                if response and response.startswith("PONG:"):
                    return port
            except (serial.SerialException, TimeoutError, OSError):
                continue
        return None

    def close(self) -> None:
        self._reader_active.clear()
        if self._reader_thread.is_alive():
            self._reader_thread.join(timeout=0.5)
        if self.serial.is_open:
            self.serial.close()

    def _reader_loop(self) -> None:
        while self._reader_active.is_set():
            try:
                raw = self.serial.readline()
            except (serial.SerialException, OSError):
                break
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            self._response_queue.put(line)
            for prefix, handlers in list(self.handlers.items()):
                if line.startswith(prefix):
                    for handler in list(handlers):
                        try:
                            handler(line)
                        except Exception:
                            continue

    def __enter__(self) -> "GlitchDongle":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
