"""
BLE Glucose Record Reader

This script connects to a Bluetooth Low Energy (BLE) glucose meter and
downloads stored glucose records using the Glucose Service defined in
the Bluetooth GATT specification.

The program performs the following steps:

1. Connects to a BLE device using its MAC address.
2. Subscribes to notifications for:
   - Glucose Measurement
   - Glucose Measurement Context
   - Record Access Control Point (RACP)
3. Sends a request to retrieve all stored glucose records.
4. Receives and parses measurement data using the glucose GATT parser.

The script relies on the Bleak library for BLE communication and a
custom parser module for decoding glucose characteristic values.
"""

import asyncio
import struct
import sys
from datetime import datetime
from bleak import BleakClient
from gatt_glucose_parser import gm_metadata, gmc_metadata, parse_gatt_glucose_message, print_parsed_data


# ---------------------------------------------------------------------
# BLE UUIDs for the Glucose Service and related characteristics
# ---------------------------------------------------------------------

GLUCOSE_SERVICE_UUID = "00001808-0000-1000-8000-00805f9b34fb"
# Glucose Measurement characteristic
GM_UUID = "00002a18-0000-1000-8000-00805f9b34fb"
# Glucose Measurement Context characteristic
GMC_UUID = "00002a34-0000-1000-8000-00805f9b34fb"
# Record Access Control Point (used to request stored records)
RACP_UUID = "00002a52-0000-1000-8000-00805f9b34fb"

# Event used to signal that all records have been received
finished_event = asyncio.Event()


def gm_handler(sender, data):
    """
    Notification handler for Glucose Measurement.

    This function is called whenever the device sends a glucose
    measurement notification.

    Args:
        sender: BLE characteristic handle that generated the notification
        data: Raw bytearray containing the measurement data
    """
    print(f"Glucose Measurement: {data}")
    values, labels = parse_gatt_glucose_message(gm_metadata, data)
    print_parsed_data(values, labels, indentation=1)


def gmc_handler(sender, data):
    """
    Notification handler for Glucose Measurement Context.

    Some devices send additional contextual information related to a
    measurement (meal, medication, exercise, etc.).

    Args:
        sender: BLE characteristic handle
        data: Raw bytearray with the context information
    """
    print(f"Glucose Measurement Context: {data}")
    values, labels = parse_gatt_glucose_message(gmc_metadata, data)
    print_parsed_data(values, labels, indentation=1)


def racp_handler(sender, data):
    """
    Notification handler for the Record Access Control Point (RACP).

    The RACP characteristic is used to control record transfers
    from the glucose meter. When the device finishes sending records,
    it sends a response indicating completion.

    Args:
        sender: BLE characteristic handle
        data: Response packet from the RACP characteristic
    """
    opcode = data[0]
    if opcode == 0x06:  # response
        response_code = data[3]
        if response_code == 0x01:
            print("All records received")
        else:
            print("RACP error:", response_code)
        finished_event.set()


def get_handle(client, uuid, service_uuid):
    """
    Retrieve the handle of a characteristic within a specific service.

    Some BLE stacks require operations to be performed using the
    characteristic handle rather than the UUID.

    Args:
        client: Connected BleakClient instance
        uuid: Characteristic UUID
        service_uuid: Service UUID containing the characteristic

    Returns:
        Integer handle of the matching characteristic
    """
    for s in client.services:
        if s.uuid.lower() == service_uuid.lower():
            for c in s.characteristics:
                if c.uuid.lower() == uuid.lower():
                    return c.handle


async def main(address):
    """
    Main asynchronous BLE workflow.

    This function connects to the glucose meter, subscribes to
    notifications, requests stored records, and waits until all
    data has been received.

    Args:
        address: BLE MAC address of the glucose device
    """
    async with BleakClient(address) as client:
        print("Connected")

        gm_handle = get_handle(client, GM_UUID, GLUCOSE_SERVICE_UUID)
        gmc_handle = get_handle(client, GMC_UUID, GLUCOSE_SERVICE_UUID)
        racp_handle = get_handle(client, RACP_UUID, GLUCOSE_SERVICE_UUID)

        await client.start_notify(gm_handle, gm_handler)
        await client.start_notify(gmc_handle, gmc_handler)
        await client.start_notify(racp_handle, racp_handler)

        print("Requesting all records...")
        await client.write_gatt_char(
            racp_handle,
            bytearray([0x01, 0x01]),
            response=True
        )

        await finished_event.wait()
        print("Download complete")


# ---------------------------------------------------------------------
# Program entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gatt_glucose_reader.py <BLE_ADDRESS>")
        sys.exit(1)

    address = sys.argv[1]
    asyncio.run(main(address))

