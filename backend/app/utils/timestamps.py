"""
Timestamp standardisation and ISO-8601 formatting utilities.
"""
from datetime import datetime, timezone
from typing import Optional, Union


def ensure_iso_timestamp(dt_input: Optional[Union[datetime, str]]) -> str:
    """Ensures input is converted to standard ISO-8601 string with timezone offset."""
    if dt_input is None:
        return datetime.now(timezone.utc).isoformat()

    if isinstance(dt_input, datetime):
        if dt_input.tzinfo is None:
            dt_input = dt_input.replace(tzinfo=timezone.utc)
        return dt_input.isoformat()

    if isinstance(dt_input, str):
        # If it's already an ISO string, return trimmed
        clean = dt_input.strip()
        if clean:
            return clean

    return datetime.now(timezone.utc).isoformat()
