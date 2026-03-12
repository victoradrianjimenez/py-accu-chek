"""
BLE GATT Glucose Data Parser

This module provides utilities to decode and parse Bluetooth Low Energy (BLE)
GATT characteristic values related to the Glucose Service.

The implementation follows the structure defined in the
Bluetooth Glucose Service specification. It converts raw byte arrays received
from BLE devices (such as glucose meters) into human-readable values.

Typical usage includes parsing data from:
- Glucose Measurement
- Glucose Measurement Context
- Glucose Features
- Device Information Service characteristics

The metadata dictionaries describe the structure of each characteristic and
are used by the generic parser to decode incoming packets.
"""

from struct import unpack, calcsize


def decode_sfloat(x: int) -> float:
    """
    Decode a 16-bit IEEE-11073 SFLOAT value.

    The SFLOAT format uses a 12-bit mantissa and a 4-bit exponent.

    Args:
        x: Unsigned 16-bit integer representing an SFLOAT value.

    Returns:
        The decoded floating-point number.
    """
    m = x & 0x0FFF
    e = (x >> 12) & 0x0F
    if m >= 0x800: m -= 0x1000
    if e >= 0x8: e -= 0x10
    return m * 10**e


def _parse_bit_list(x, l: dict):
    """
    Convert a bitmask value into a list of human-readable descriptions.

    Args:
        x: Integer containing bit flags.
        l: Dictionary mapping bit positions to descriptions.

    Returns:
        Tuple containing descriptions for all active bits.
    """
    return tuple(l.get(b, '-') for b in range(16) if (x >> b) & 1)


# ---------------------------------------------------------------------
# Dictionaries describing enumerated values used by BLE characteristics
# ---------------------------------------------------------------------

# Meal type associated with the glucose measurement
meal_dict = {
    0:"Reserved for future use",
    1:"Preprandial (before meal)",
    2:"Postprandial (after meal)",
    3:"Fasting",
    4:"Casual (snacks, drinks, etc.)",
    5:"Bedtime"
}

# Type of person performing the test
tester_dict = {
    0:"Reserved for future use",
    1:"Self",
    2:"Health Care Professional",
    3:"Lab test",
    15:"Tester value not available"
}

# Health condition of the user
health_dict = {
    0:"Reserved for future use",
    1:"Minor health issues",
    2:"Major health issues",
    3:"During menses",
    4:"Under stress",
    5:"No health issues",
    15:"Health value not available"
}

# Medication type
medication_id_dict = {
    0:"Reserved for future use",
    1:"Rapid acting insulin",
    2:"Short acting insulin",
    3:"Intermediate acting insulin",
    4:"Long acting insulin",
    5:"Pre-mixed insulin"
}

# Carbohydrate intake classification
carbohydrate_id_dict = {
    0:"Reserved for future use",
    1:"Breakfast",
    2:"Lunch",
    3:"Dinner",
    4:"Snack",
    5:"Drink",
    6:"Supper",
    7:"Brunch"
}

# Sensor error/status flags reported during measurement
sensor_status_annunciation_dict = {
    0:"Device battery low at time of measurement",
    1:"Sensor malfunction or faulting at time of measurement",
    2:"Sample size for blood or control solution insufficient at time of measurement",
    3:"Strip insertion error",
    4:"Strip type incorrect for device",
    5:"Sensor result higher than the device can process",
    6:"Sensor result lower than the device can process",
    7:"Sensor temperature too high for valid test/result at time of measurement",
    8:"Sensor temperature too low for valid test/result at time of measurement",
    9:"Sensor read interrupted because strip was pulled too soon at time of measurement",
    10:"General device fault has occurred in the sensor",
    11:"Time fault has occurred in the sensor and time may be inaccurate"
}

# Sample type and sampling location
type_location_dict = {
    0:"Reserved for future use",
    1:"Capillary Whole blood",
    2:"Capillary Plasma",
    3:"Venous Whole blood",
    4:"Venous Plasma",
    5:"Arterial Whole blood",
    6:"Arterial Plasma",
    7:"Undetermined Whole blood",
    8:"Undetermined Plasma",
    9:"Interstitial Fluid (ISF)",
    10:"Control Solution"
}

sample_location_dict = {
    0:"Reserved for future use",
    1:"Finger",
    2:"Alternate Site Test (AST)",
    3:"Earlobe",
    4:"Control solution",
    15:"Not available"
}

glucose_feature_dict = {
    0:"Low Battery Detection During Measurement Supported",
    1:"Sensor Malfunction Detection Supported",
    2:"Sensor Sample Size Supported",
    3:"Sensor Strip Insertion Error Detection Supported",
    4:"Sensor Strip Type Error Detection Supported",
    5:"Sensor Result High-Low Detection Supported",
    6:"Sensor Temperature High-Low Detection Supported",
    7:"Sensor Read Interrupt Detection Supported",
    8:"General Device Fault Supported",
    9:"Time Fault Supported",
    10:"Multiple Bond Supported"
}

category_dict = {
    0:"Unknown",
    64:"Generic Phone",
    128:"Generic Computer",
    192:"Generic Watch",
    193:"Watch: Sports Watch",
    256:"Generic Clock",
    320:"Generic Display",
    384:"Generic Remote Control",
    448:"Generic Eye-glasses",
    512:"Generic Tag",
    576:"Generic Keyring",
    640:"Generic Media Player",
    704:"Generic Barcode Scanner",
    768:"Generic Thermometer",
    769:"Thermometer: Ear",
    832:"Generic Heart rate Sensor",
    833:"Heart Rate Sensor: Heart Rate Belt",
    896:"Generic Blood Pressure",
    897:"Blood Pressure: Arm",
    898:"Blood Pressure: Wrist",
    960:"Human Interface Device (HID)",
    961:"Keyboard",
    962:"Mouse",
    963:"Joystick",
    964:"Gamepad",
    965:"Digitizer Tablet",
    966:"Card Reader",
    967:"Digital Pen",
    968:"Barcode Scanner",
    1024:"Generic Glucose Meter",
    1088:"Generic: Running Walking Sensor",
    1089:"Running Walking Sensor: In-Shoe",
    1090:"Running Walking Sensor: On-Shoe",
    1091:"Running Walking Sensor: On-Hip",
    1152:"Generic: Cycling",
    1153:"Cycling: Cycling Computer",
    1154:"Cycling: Speed Sensor",
    1155:"Cycling: Cadence Sensor",
    1156:"Cycling: Power Sensor",
    1157:"Cycling: Speed and Cadence Sensor",
    3136:"Generic: Pulse Oximeter",
    3137:"Fingertip",
    3138:"Wrist Worn",
    3200:"Generic: Weight Scale",
    3264:"Generic Personal Mobility Device",
    3265:"Powered Wheelchair",
    3266:"Mobility Scooter",
    3328:"Generic Continuous Glucose Monitor",
    3392:"Generic Insulin Pump",
    3393:"Insulin Pump, durable pump",
    3396:"Insulin Pump, patch pump",
    3400:"Insulin Pen",
    3456:"Generic Medication Delivery",
    5184:"Generic: Outdoor Sports Activity",
    5185:"Location Display Device",
    5186:"Location and Navigation Display Device",
    5187:"Location Pod",
    5188:"Location and Navigation Pod"
}

gm_metadata = {
    "flags": ("Flags", 'B', None, 0, 0), #8bits
    "seq_num": ("Sequence Number", 'H', None, 0, 0), #uint16
    "year": ("Year", 'H', None, 0, 0), #uint16
    "month": ("Month", 'B', None, 0, 0), #uint8
    "day": ("Day", 'B', None, 0, 0), #uint8
    "hours": ("Hours", 'B', None, 0, 0), #uint8
    "minutes": ("Minutes", 'B', None, 0, 0), #uint8
    "seconds": ("Seconds", 'B', None, 0, 0), #uint8
    "time_offset": ("Time Offset (min)", 'h', None, 0b0001, 0b0001), #int16
    "glucose_mg_dL": ("Glucose Concentration (mg/dL)", 'H', lambda x: decode_sfloat(x) * 1e5, 0b0110, 0b0010), #sfloat
    "glucose_mol_L": ("Glucose Concentration (mo/L)", 'H', lambda x: decode_sfloat(x) * 1e3, 0b0110, 0b0110), #sfloat
    "location": ("Type-Sample Location", 'B', lambda x: (type_location_dict.get(x & 0x0F, "-"), sample_location_dict.get(x >> 4, "-")), 0b0010, 0b0010), #2*nibble
    "sensor_status": ("Sensor Status Annunciation", 'H', lambda x: _parse_bit_list(x, sensor_status_annunciation_dict), 0b1000, 0b1000), #16bits
}

# Glucose Measurement Context
gmc_metadata = {
    "flags": ("Flags", 'B', None, 0, 0), #8bits
    "seq_num": ("Sequence Number", 'H', None, 0, 0), #uint16
    "flags_ex": ("Extended Flags", 'B', None, 0b10000000, 0b10000000), #8bits
    "carbohydrate_id": ("Carbohydrate ID", 'B', lambda x: carbohydrate_id_dict.get(x, '-'), 0b0001, 0b0001), #uint8
    "carbohydrate": ("Carbohydrate (gr)", 'H', lambda x: decode_sfloat(x), 0b0001, 0b0001), #sfloat
    "meal": ("Meal", 'B', lambda x: meal_dict.get(x, '-'), 0b0010, 0b0010), #uint8
    "tester_health": ("Tester-Health", 'B', lambda x: (tester_dict.get(x & 0x0F, "-"), health_dict.get(x >> 4, "-")), 0b0100, 0b0100), #2*nibble
    "exercise_duration": ("Exercise Duration (sec)", 'H', None, 0b1000, 0b1000), #uint16
    "exercise_intensity": ("Exercise Intensity (%)", 'B', None, 0b1000, 0b1000), #uint8
    "medication": ("Medication", 'B', lambda x: medication_id_dict.get(x,"-"), 0b10000, 0b10000), #uint8
    "medication_mg": ("Medication (mg)", 'H', lambda x: decode_sfloat(x), 0b110000, 0b010000), #sfloat
    "medication_mlt": ("Medication (mlt)", 'H', lambda x: decode_sfloat(x), 0b110000, 0b110000), #sfloat
    "hba1c": ("HbA1c (%)", 'H', lambda x: decode_sfloat(x), 0b1000000, 0b1000000), #sfloat
}

# Glucose / Glucose Feature
GF_metadata = {
    "feature": ("Glucose Feature", 'H', lambda x: _parse_bit_list(x, glucose_feature_dict)) #uint16
}

# Glucose / Date Time
dt_metadata = {
    "year": ("Year", 'H', None), #uint16
    "month": ("Month", 'B', None), #uint8
    "day": ("Day", 'B', None), #uint8
    "hours": ("Hours", 'B', None), #uint8
    "minutes": ("Minutes", 'B', None), #uint8
    "seconds": ("Seconds", 'B', None), #uint8
}

# Device Information / PnP ID
PNP_metadata = {
    "vendor_id_src": ("Vendor ID Source", 'B', None),
    "vendor_id": ("Vendor ID", 'H', None),
    "product_id": ("Product ID", 'H', None),
    "version": ("Product Version", "H", None) #uint16
}

# Device Information / System ID
SID_metadata = {
    "manufacturer_identifier": ("Manufacturer-Organizationally Unique Identifiers", 'Q', lambda x: (x>>24, x & 16777215)) #uint64
}

# Device Information / Appearance
APA_metadata = {
    "category": ("Category", 'H', lambda x: category_dict.get(x, '-')) #uint16
}



# ---------------------------------------------------------------------
# Generic parser functions
# ---------------------------------------------------------------------

def parse_gatt_message(metadata, data):
    """
    Parse a BLE GATT characteristic according to a metadata definition.

    Args:
        metadata:
            Dictionary describing the structure of the characteristic.
            Each entry contains:
                (label, struct_format, decoder_function)

        data:
            Raw bytearray received from the BLE device.

    Returns:
        Tuple containing:
            values -> dictionary with parsed values
            labels -> dictionary with human-readable labels
    """
    format_struct = '<' + ''.join([v[1] for v in metadata.values()])
    expected_size = calcsize(format_struct)
    if len(data) < expected_size:
        raise ValueError("Packet too short")
    res = unpack(format_struct, data)
    values = {k: v[2](res[i]) if v[2] != None else res[i] for i, (k, v) in enumerate(metadata.items())}
    labels = {k: v[0] for i, (k, v) in enumerate(metadata.items())}
    return values, labels


def parse_gatt_glucose_message(metadata, data):
    """
    Parse a glucose service message that contains optional fields
    controlled by a Flags byte.

    Args:
        metadata: Metadata dictionary describing the message structure
        data: Raw BLE characteristic value

    Returns:
        Parsed values and labels
    """
    metadata = {k: v for k, v in metadata.items() if (data[0] & v[3]) == v[4]}
    return parse_gatt_message(metadata, data)


def print_parsed_data(values, labels, indentation=0):
    """
    Pretty-print parsed GATT data.

    Args:
        values: Parsed values dictionary
        labels: Labels dictionary
        indentation: Indentation level for formatted output
    """
    for k in values:
        if isinstance(values[k], tuple):
            print(f"{' '*(indentation*4)}{labels[k]}:")
            for i in values[k]:
                print(f"{' '*(((indentation+1))*4)}{i}")                
        else:
            print(f"{' '*(indentation*4)}{labels[k]}: {values[k]}")


if __name__ == "__main__":
    
    print("Glucose Measurement")
    data = bytearray(b'\x1b\x07\x00\xe4\x07\x07\x05\x01\x25\x36\x3c\x00\x59\xb1\xf8\x00\x00')
    print_parsed_data(*parse_gatt_glucose_message(gm_metadata, data), indentation=1)

    print('Glucose Measurement Context')
    data = bytearray(b'\x02\x07\x00\x01')
    print_parsed_data(*parse_gatt_glucose_message(gmc_metadata, data), indentation=1)

    # Accu-Chek data requested calling read:

    print("Glucose / Date Time")
    data = bytearray(b'\xe4\x07\x07\x13\x00\x1a\x00')
    print_parsed_data(*parse_gatt_message(dt_metadata, data), indentation=1)

    print("Glucose / Glucose Feature")
    data = bytearray(b' \x06')
    print_parsed_data(*parse_gatt_message(GF_metadata, data), indentation=1)

    print("Device Information / PnP ID")
    data = bytearray(b'\x01p\x01\xd5!r\x01')
    print_parsed_data(*parse_gatt_message(PNP_metadata, data), indentation=1)

    print("Device Information / System ID")
    data = bytearray(b'\x02\x82\xb8\x01\x00\x19`\x00')
    print_parsed_data(*parse_gatt_message(SID_metadata, data), indentation=1)

    print("Device Information / Model Number String")
    data = bytearray(b'925')
    print(f"{' '*4}{data.decode()}")

    print("Device Information / Serial Number String")
    data = bytearray(b'92511502082')
    print(f"{' '*4}{data.decode()}")

    print("Device Information / Firmware Revision String")
    data = bytearray(b'v1.9.6')
    print(f"{' '*4}{data.decode()}")

    print("Device Information / Manufacturer Name String")
    data = bytearray(b'Roche')
    print(f"{' '*4}{data.decode()}")
    
    print("Device Information / IEEE 11073-20601 Regulatory Cert. Data List")
    data = bytearray(b'\x00\x02\x00\x12\x02\x01\x00\x08\x04\x01\x00\x01\x00\x02\x80\x11\x02\x02\x00')
    print(f"{' '*4}{data}")

    print("Device Information / Device Name")
    data = bytearray(b'meter+11502082')
    print(f"{' '*4}{data.decode()}")

    print("Device Information / Appearance")
    data = bytearray(b'\x00\x04')
    print_parsed_data(*parse_gatt_message(APA_metadata, data), indentation=1)

