import asyncio
import sys
from bleak import BleakClient


async def main(address):
	async with BleakClient(address) as client:
		for service in client.services:
			print(service.uuid)
			for char in service.characteristics:
				print("  char:", char.uuid, "handle:", char.handle)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ble_list_characteristics.py <BLE_ADDRESS>")
        sys.exit(1)

    address = sys.argv[1]
    asyncio.run(main(address))

