"""Utility functions for parsing configs."""

import re


def parse_time(time_str: str) -> int:
    """
    Parse a time string into milliseconds.

    Args:
        time_str: Time string with optional decimal value and unit
                  (e.g., '10ms', '2s', '1.5m', '1h')

    Returns:
        Time in milliseconds as integer

    Raises:
        ValueError: If format is invalid or unit is not recognized
    """
    match = re.match(r"(\d+(?:\.\d+)?) *(ms|s|m|h)", time_str.strip())
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")
    value, unit = match.groups()
    value = float(value)
    match unit:
        case 'ms':
            return int(value)
        case 's':
            return int(value * 1000)
        case 'm':
            return int(value * 60 * 1000)
        case 'h':
            return int(value * 3600 * 1000)
        case _:
            raise ValueError(f"Unknown time unit: {unit}")


def parse_bytes(byte_str: str) -> int:
    """
    Parse a byte size string into bytes.

    Args:
        byte_str: Size string with value and unit (e.g., '10B', '2kB', '1.5MB', '1GB')

    Returns:
        Size in bytes as integer

    Raises:
        ValueError: If format is invalid or unit is not recognized
    """
    match = re.match(r"(-?\d+(?:\.\d+)?) *(B|kB|MB|GB)", byte_str.strip())
    if not match:
        raise ValueError(f"Invalid size format: {byte_str}")
    value, unit = match.groups()
    value = float(value)
    match unit:
        case 'B':
            return int(value)
        case 'kB':
            return int(value * 1_000)
        case 'MB':
            return int(value * 1_000_000)
        case 'GB':
            return int(value * 1_000_000_000)
        case _:
            raise ValueError(f"Unknown unit: {unit}")
