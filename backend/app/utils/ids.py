"""
Identifier formatting and generation utilities.
"""
import uuid


def generate_uuid() -> str:
    """Generates a standard random UUID4 string."""
    return str(uuid.uuid4())


def generate_event_id() -> str:
    """Generates a standard event ID string."""
    return f"evt_{uuid.uuid4().hex[:12]}"


def generate_incident_id() -> str:
    """Generates a standard incident ID string."""
    return f"inc_{uuid.uuid4().hex[:12]}"
