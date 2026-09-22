# Direct Bluetooth LE input for MYOblue_GUI (no USB dongle needed).
#
# BleSerial connects to every MYOblue sensor in range and exposes the same
# byte stream the dongle writes to its serial port ([0xFF, 0xFF] + 244-byte
# packet per message), with the small subset of the pyserial API that
# SerialMonitor uses. Requires the `bleak` package.

import asyncio
import re
import sys
import threading
import time

try:
    from bleak import BleakClient, BleakScanner
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

PORT_NAME = "Bluetooth (no dongle)"
TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Nordic UART Service, notify
NAME_RE = re.compile(r"^\d+_MYOblue")
HEADER = b"\xff\xff"
MAX_BUFFER = 246 * 2000  # ~4 min of one sensor; oldest data is dropped past this


def log(msg):
    print(time.strftime("[%H:%M:%S] ") + "BLE: " + msg, flush=True)


def bluez_timing_ok():
    """MYOblue sensors drop links made with BlueZ's default 420 ms supervision timeout."""
    if not sys.platform.startswith("linux"):
        return True
    try:
        with open("/etc/bluetooth/main.conf") as f:
            return re.search(r"^ConnectionSupervisionTimeout\s*=", f.read(), re.M) is not None
    except OSError:
        return True


class BleSerial:
    def __init__(self):
        self.is_open = False
        self.dtr = self.rts = True  # accepted and ignored, like the dongle
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._loop = None
        self._thread = None
        self._stop = None

    # --- pyserial-compatible surface used by SerialMonitor ---
    def open(self):
        if self.is_open:
            return
        if not bluez_timing_ok():
            log("WARNING: add the [LE] connection settings from README.md to /etc/bluetooth/main.conf, "
                "or the sensors will keep disconnecting.")
        self.is_open = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def close(self):
        if not self.is_open:
            return
        self.is_open = False
        if self._loop and self._stop:
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._thread:
            self._thread.join(timeout=5)
        self.flushInput()

    @property
    def in_waiting(self):
        return len(self._buf)

    def read(self, size=1):
        with self._lock:
            data = bytes(self._buf[:size])
            del self._buf[:size]
        return data

    def flushInput(self):
        with self._lock:
            self._buf.clear()

    reset_input_buffer = flushInput

    # --- BLE side ---
    def _on_packet(self, data):
        with self._lock:
            self._buf += HEADER + bytes(data)
            if len(self._buf) > MAX_BUFFER:
                del self._buf[:len(self._buf) - MAX_BUFFER]

    def _run(self):
        self._loop = asyncio.new_event_loop()
        try:
            self._loop.run_until_complete(self._main())
        finally:
            self._loop.close()

    async def _main(self):
        self._stop = asyncio.Event()
        connect_lock = asyncio.Lock()  # BlueZ allows one pending connect at a time
        known, tasks = set(), []

        def found(device, adv):
            name = device.name or adv.local_name or ""
            if NAME_RE.match(name) and device.address not in known:
                known.add(device.address)
                log(f"found {name}")
                tasks.append(asyncio.ensure_future(self._sensor(device, name, connect_lock)))

        scanner = BleakScanner(found)
        await scanner.start()
        log("scanning for MYOblue sensors (switch them on)")
        await self._stop.wait()
        await scanner.stop()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        log("stopped")

    async def _sensor(self, device, name, connect_lock):
        client = None
        try:
            while not self._stop.is_set():
                try:
                    async with connect_lock:
                        client = BleakClient(device, timeout=20)
                        await client.connect()
                    await client.start_notify(TX_UUID, lambda _, d: self._on_packet(d))
                    log(f"{name}: streaming")
                    while client.is_connected and not self._stop.is_set():
                        await asyncio.sleep(0.3)
                    if not self._stop.is_set():
                        log(f"{name}: disconnected, reconnecting")
                except Exception as e:
                    log(f"{name}: connect failed ({type(e).__name__}), retrying")
                if self._stop.is_set():
                    break
                await asyncio.sleep(1)
                fresh = await BleakScanner.find_device_by_address(device.address, timeout=10)
                if fresh:
                    device = fresh
        finally:
            if client and client.is_connected:
                await client.disconnect()
