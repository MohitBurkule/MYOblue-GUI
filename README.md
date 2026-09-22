# MYOblue-GUI v1.2.2

This repository contains the source code of the MYOblue-GUI v1.2.2

## 1 Introduction

MYOblue_GUI - is powerful and easy to use, free, open-source, cross-platform Python-based graphical interface for EMG analysis using MYOblue sensors. MYOblue GUI provides real-time visualization, analysis, recording and processing of EMG and ECG signals.

Supported operating systems: **Windows**, **Linux**, **macOS**.

## 2 EMG Analysis Features
- in-depth EMG signal analysis.
- real-time display of **raw**, **rectified**, **smoothed**, and **RMS** signals from up to eight MYOblue sensors.
- real-time **FFT** analysys of EMG signals.
- band-pass and 50/60 Hz notch filters.
- **record and playback** up to eight **synchronized** channels.
- recording EMG to a ".txt" file for import into external programs.

## Bluetooth without the USB dongle (fork addition)

MYOblue sensors are plain Bluetooth LE devices (Nordic UART Service), so the GUI can also talk to them with the computer's own Bluetooth. Pick **Bluetooth (no dongle)** in the port list; it connects to every MYOblue sensor in range and reconnects automatically. The code is in `myoblue_ble.py` and needs the `bleak` package, which the GUI installs on first launch like its other dependencies.

- Unplug the USB dongle first, or it will grab the sensors before the computer can.
- Sensors stop advertising a few minutes after power-on if nothing connects; power-cycle them if they are not found.
- **Linux:** BlueZ's default link supervision timeout (420 ms) is too short for these sensors and every connection fails with HCI error 0x3e. Add this to `/etc/bluetooth/main.conf` (the `[LE]` section already exists, the keys are commented out) and run `sudo systemctl restart bluetooth`:

  ```ini
  [LE]
  MinConnectionInterval=24
  MaxConnectionInterval=24
  ConnectionSupervisionTimeout=400
  ```

  This matches what the dongle uses (30 ms interval, 4 s supervision timeout).
- **Linux serial permissions** (for the dongle): add yourself to the `uucp` group, or install a udev rule such as `SUBSYSTEM=="tty", ATTRS{idVendor}=="1915", ATTRS{idProduct}=="521a", TAG+="uaccess"`.

## 3 Support

If you need assistance, please contact us ([contacts](https://elemyo.com/support/contacts)).

## 4 License
Completely **free** and open-source.

The code contained in this repository and the executable distributions are licensed under the terms of the MIT license. If you have questions about licensing please contact us ([contacts](https://elemyo.com/support/contacts)).
