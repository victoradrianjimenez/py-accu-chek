# BLE Glucose Meter Reader

A Python tool to download and decode glucose measurements from Bluetooth Low Energy (BLE) glucose meters using the **Bluetooth Glucose Service**.

The program connects to a BLE glucose device, requests stored records, receives notifications, and decodes the measurements into human-readable values.

This project uses **Bleak** for BLE communication and a custom parser for decoding GATT glucose characteristics.

---

# Features

* Connects to BLE glucose meters
* Requests all stored glucose records
* Parses:
  * Glucose Measurement
  * Glucose Measurement Context
  * Device information
* Decodes IEEE-11073 SFLOAT values
* Converts raw BLE packets into readable measurements
* Works asynchronously using `asyncio`

---

# Requirements

* Python 3.9+
* A computer with Bluetooth Low Energy support

Install dependencies:

```
pip install bleak
```

This project uses the Python library **Bleak** for BLE communication.

---

# Bluetooth Architecture Overview

BLE devices expose data using the **GATT (Generic Attribute Profile)** model:

```
BLE Device
   │
   └── Service
         │
         └── Characteristic
               │
               └── Value
```

This project interacts with the **Glucose Service**, which contains the following characteristics:

| Characteristic              | UUID     | Description                     |
| --------------------------- | -------- | ------------------------------- |
| Glucose Measurement         | `0x2A18` | Contains glucose readings       |
| Glucose Measurement Context | `0x2A34` | Optional contextual information |
| Record Access Control Point | `0x2A52` | Used to request stored records  |

---

# Usage

Run the reader by passing the BLE device address:

```
python gatt_glucose_reader.py <BLE_ADDRESS>
```

