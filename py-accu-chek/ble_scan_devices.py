import asyncio
from bleak import BleakScanner


async def scan():
	devices = await BleakScanner.discover()
	for d in devices:
		print(f"{d.name} - {d.address}")


if __name__ == "__main__":
    asyncio.run(scan())
