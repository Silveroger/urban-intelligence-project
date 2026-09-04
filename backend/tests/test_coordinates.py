import pytest
from app.utils.coordinates import (
    validate_coordinates,
    point_to_wkt,
    linestring_to_geojson_coords,
    point_to_geojson_coords,
)


def test_validate_coordinates_valid():
    validate_coordinates(30.7333, 76.7794)
    validate_coordinates(0.0, 0.0)
    validate_coordinates(-90.0, -180.0)
    validate_coordinates(90.0, 180.0)


def test_validate_coordinates_invalid():
    with pytest.raises(ValueError):
        validate_coordinates(95.0, 76.7794)

    with pytest.raises(ValueError):
        validate_coordinates(30.7333, 185.0)


def test_point_to_wkt():
    wkt = point_to_wkt(76.7794, 30.7333)
    assert wkt == "SRID=4326;POINT(76.7794 30.7333)"


def test_linestring_to_geojson_coords():
    # From GeoJSON string
    geojson_str = '{"type": "LineString", "coordinates": [[76.77, 30.73], [76.78, 30.74]]}'
    coords = linestring_to_geojson_coords(geojson_str)
    assert len(coords) == 2
    assert coords[0] == [76.77, 30.73]

    # From WKT
    wkt_str = "LINESTRING(76.77 30.73, 76.78 30.74)"
    coords_wkt = linestring_to_geojson_coords(wkt_str)
    assert len(coords_wkt) == 2
    assert coords_wkt[0] == [76.77, 30.73]


def test_point_to_geojson_coords():
    wkt_point = "POINT(76.7794 30.7333)"
    coords = point_to_geojson_coords(wkt_point)
    assert coords == (76.7794, 30.7333)
