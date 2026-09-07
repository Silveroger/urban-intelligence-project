"""
Coordinate standards and spatial transformation utilities.
All API exchanges adhere to GeoJSON standard: [longitude, latitude].
"""
from typing import List, Tuple, Union
import json


def validate_coordinates(lat: float, lng: float) -> None:
    """Validates WGS84 latitude (-90 to 90) and longitude (-180 to 180)."""
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude must be between -90 and 90 degrees, got {lat}")
    if not (-180.0 <= lng <= 180.0):
        raise ValueError(f"Longitude must be between -180 and 180 degrees, got {lng}")


def point_to_wkt(lng: float, lat: float) -> str:
    """Returns WKT string for a POINT(lng lat)."""
    validate_coordinates(lat, lng)
    return f"SRID=4326;POINT({lng} {lat})"


def linestring_to_geojson_coords(geometry_data: Union[str, dict, None]) -> List[List[float]]:
    """
    Parses LineString geometry into list of [lng, lat] coordinate pairs.
    Handles GeoJSON string, dict, or WKT.
    """
    if geometry_data is None:
        return []

    if isinstance(geometry_data, str):
        try:
            parsed = json.loads(geometry_data)
            if isinstance(parsed, dict) and "coordinates" in parsed:
                return parsed["coordinates"]
        except Exception:
            pass

        # Handle simple WKT LINESTRING(...)
        clean = geometry_data.strip()
        if "LINESTRING" in clean.upper():
            start = clean.find("(")
            end = clean.rfind(")")
            if start != -1 and end != -1:
                coord_str = clean[start + 1:end].strip()
                coords = []
                for pt in coord_str.split(","):
                    parts = pt.strip().split()
                    if len(parts) >= 2:
                        coords.append([float(parts[0]), float(parts[1])])
                return coords

    elif isinstance(geometry_data, dict):
        if "coordinates" in geometry_data:
            return geometry_data["coordinates"]

    return []


def point_to_geojson_coords(geometry_data: Union[str, dict, object, None]) -> Tuple[float, float]:
    """
    Parses Point geometry into (longitude, latitude).
    Handles GeoJSON dict/string, WKT, WKBElement, and raw bytes.
    """
    if geometry_data is None:
        return (0.0, 0.0)

    # Handle WKBElement or binary WKB
    raw_bytes = None
    if hasattr(geometry_data, "data"):
        raw_bytes = bytes(geometry_data.data)
    elif isinstance(geometry_data, (bytes, bytearray)):
        raw_bytes = bytes(geometry_data)

    if raw_bytes and len(raw_bytes) >= 16:
        try:
            import struct
            byte_order = "<" if raw_bytes[0] == 1 else ">"
            lng, lat = struct.unpack(f"{byte_order}dd", raw_bytes[-16:])
            return (float(lng), float(lat))
        except Exception:
            pass

    if isinstance(geometry_data, str):
        try:
            parsed = json.loads(geometry_data)
            if isinstance(parsed, dict) and "coordinates" in parsed:
                coords = parsed["coordinates"]
                return (float(coords[0]), float(coords[1]))
        except Exception:
            pass

        clean = geometry_data.strip()
        if "POINT" in clean.upper():
            start = clean.find("(")
            end = clean.rfind(")")
            if start != -1 and end != -1:
                parts = clean[start + 1:end].strip().split()
                if len(parts) >= 2:
                    return (float(parts[0]), float(parts[1]))

    elif isinstance(geometry_data, dict):
        if "coordinates" in geometry_data:
            coords = geometry_data["coordinates"]
            return (float(coords[0]), float(coords[1]))

    return (0.0, 0.0)
