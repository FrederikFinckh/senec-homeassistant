#!/usr/bin/env python3
"""
senec_decode.py - Decode SENEC JSON API responses to human-readable values.

Reads a SENEC JSON response from stdin and outputs decoded JSON to stdout.

Usage:
    cat response1.json | python3 senec_decode.py
    curl -s -X POST http://<IP>/lala.cgi -d '...' | python3 senec_decode.py

The SENEC API encodes values with type prefixes:
    fl_XXXXXXXX  -> IEEE 754 float (big-endian)
    u8_XX        -> unsigned 8-bit int
    u1_XXXX      -> unsigned 16-bit int
    u3_XXXXXXXX  -> unsigned 32-bit int
    u6_...       -> unsigned 64-bit int
    i1_XXXX      -> signed 16-bit int
    i3_XXXXXXXX  -> signed 32-bit int
    i8_XX        -> signed 8-bit int
    st_...       -> string
"""

import json
import struct
import sys


def decode_value(val):
    """Decode a single SENEC type-prefixed hex value to a Python value."""
    if not isinstance(val, str) or '_' not in val:
        return val

    # Handle error/special values
    if val in ("FORBIDDEN", "VARIABLE_NOT_FOUND", "OBJECT_NOT_FOUND", "MALFORMED_VALUE"):
        return None

    prefix, hex_part = val.split('_', 1)

    if prefix == 'fl':
        return round(struct.unpack('>f', bytes.fromhex(hex_part))[0], 2)
    elif prefix in ('u8',):
        return int(hex_part, 16)
    elif prefix in ('u1',):
        return int(hex_part, 16)
    elif prefix in ('u3',):
        return int(hex_part, 16)
    elif prefix in ('u6',):
        return int(hex_part, 16)
    elif prefix == 'i1':
        v = int(hex_part, 16)
        return v - 65536 if v & 0x8000 else v
    elif prefix == 'i3':
        v = int(hex_part, 16)
        return v - 4294967296 if v & 0x80000000 else v
    elif prefix == 'i8':
        v = int(hex_part, 16)
        return v - 256 if v & 0x80 else v
    elif prefix == 'st':
        return hex_part
    elif prefix in ('ch', 'er'):
        return hex_part
    else:
        return val


def decode_recursive(obj):
    """Recursively decode all values in a nested dict/list structure."""
    if isinstance(obj, dict):
        return {k: decode_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decode_recursive(item) for item in obj]
    elif isinstance(obj, str):
        return decode_value(obj)
    return obj


def add_computed_fields(decoded):
    """Add computed summary fields based on decoded data."""
    summary = {}

    # Compute per-string and total inverter power from PV1.MPP_POWER
    if 'PV1' in decoded and 'MPP_POWER' in decoded['PV1']:
        mpp_power = decoded['PV1']['MPP_POWER']
        for i, p in enumerate(mpp_power):
            summary[f'MPP{i+1}_POWER_W'] = round(p, 2) if isinstance(p, (int, float)) else p
        total = sum(p for p in mpp_power if isinstance(p, (int, float)))
        summary['INVERTER_POWER_TOTAL_W'] = round(total, 2)

    # Per-string voltage and current
    if 'PV1' in decoded:
        if 'MPP_VOL' in decoded['PV1']:
            for i, v in enumerate(decoded['PV1']['MPP_VOL']):
                summary[f'MPP{i+1}_VOLTAGE_V'] = round(v, 2) if isinstance(v, (int, float)) else v
        if 'MPP_CUR' in decoded['PV1']:
            for i, c in enumerate(decoded['PV1']['MPP_CUR']):
                summary[f'MPP{i+1}_CURRENT_A'] = round(c, 2) if isinstance(c, (int, float)) else c

    # GUI values from ENERGY object (pre-computed by firmware)
    if 'ENERGY' in decoded:
        energy = decoded['ENERGY']
        field_map = {
            'GUI_INVERTER_POWER': 'GUI_INVERTER_POWER_W',
            'GUI_HOUSE_POW': 'GUI_HOUSE_POWER_W',
            'GUI_GRID_POW': 'GUI_GRID_POWER_W',
            'GUI_BAT_DATA_POWER': 'GUI_BATTERY_POWER_W',
            'GUI_BAT_DATA_FUEL_CHARGE': 'GUI_BATTERY_SOC_PCT',
            'STAT_STATE': 'SYSTEM_STATE_CODE',
        }
        for src, dst in field_map.items():
            if src in energy:
                v = energy[src]
                summary[dst] = round(v, 2) if isinstance(v, float) else v

    # Battery DC current
    if 'BAT1OBJ1' in decoded and 'I_DC' in decoded['BAT1OBJ1']:
        summary['BATTERY_DC_CURRENT_A'] = decoded['BAT1OBJ1']['I_DC']

    return summary


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        print("Error: no input received on stdin", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    decoded = decode_recursive(data)
    summary = add_computed_fields(decoded)

    output = {
        "summary": summary,
        "decoded": decoded,
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
