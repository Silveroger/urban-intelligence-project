"""
Builds canonical, authentic OpenStreetMap-based geometries for the 10 Chandigarh Corridors.
Saves to backend/data/chandigarh_roads_canonical.geojson
"""
import json
import os
import math

raw_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "chandigarh_osm_raw.json"))
with open(raw_path, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

elements = raw_data.get("elements", [])
ways_by_id = {w["id"]: w for w in elements if "geometry" in w}

def dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def chain_way_ids(way_chain):
    """
    way_chain: list of (way_id, is_reversed)
    Returns list of [lon, lat] rounded to 6 decimals, without duplicates.
    """
    coords = []
    for wid, is_rev in way_chain:
        w = ways_by_id[wid]
        pts = [[round(p["lon"], 6), round(p["lat"], 6)] for p in w["geometry"]]
        if is_rev:
            pts.reverse()
        if not coords:
            coords.extend(pts)
        else:
            # If start of pts is close to tail of coords, skip first point
            if dist(coords[-1], pts[0]) < 0.0001:
                coords.extend(pts[1:])
            else:
                coords.extend(pts)
    return coords

# 1. Madhya Marg (Sector 17-18): Rose Garden / Matka Chowk -> Sector 17/9 Chowk -> Press Chowk -> Transport Chowk
# Ways: 1030586415, 1031897143, 1214001325, 129584345, 129584347
c1_coords = chain_way_ids([
    (1030586415, False),
    (1031897143, False),
    (1214001325, False),
    (129584345, False),
    (129584347, False),
])

# 2. Dakshin Marg (Sector 22-35): Kisan Bhawan Chowk -> Aroma Chowk
# Ways: 1061489829, 1216415330, 129464029, 1216801261, 1061964636, 1061964640, 129460470
c2_coords = chain_way_ids([
    (1061489829, False),
    (1216415330, False),
    (129464029, False),
    (1216801261, False),
    (1061964636, False),
    (1061964640, False),
    (129460470, False),
])

# 3. Jan Marg (Sector 9-17): Capitol Complex / Sector 9 down to Matka Chowk & Sector 17
# Ways: 129720597, 1035053137 (rev), 1213766516, 1213766515, 129720599
c3_coords = chain_way_ids([
    (129720597, False),
    (1035053137, True),
    (1213766516, False),
    (1213766515, False),
    (129720599, False),
])

# 4. Himalaya Marg (Sector 22-23): Sec 16/17/22/23 Chowk down to Kisan Bhawan Chowk
# Ways: 1061964633, 129464032, 1062538286, 1061964632, 1061964631, 1061964630
c4_coords = chain_way_ids([
    (1061964633, False),
    (129464032, False),
    (1062538286, False),
    (1061964632, False),
    (1061964631, False),
    (1061964630, False),
])

# 5. Udyog Path (Sector 14-25 Corridor): From Sec 14/15/24/25 Chowk along Udyog Path towards Panjab University
# Ways: 129476916 (rev), 129476917 (rev), 575390847, 129476913, 129476918 (rev)
c5_coords = chain_way_ids([
    (129476916, True),
    (129476917, True),
    (575390847, False),
    (129476913, False),
    (129476918, True),
])

# 6. Purv Marg (Sector 26-27): From Tribune Chowk / Sec 27 up to Transport Chowk (Sector 26)
# Ways: 1282082635, 1213766499, 287882377, 177266071
c6_coords = chain_way_ids([
    (1282082635, False),
    (1213766499, False),
    (287882377, False),
    (177266071, False),
])

# 7. Sarovar Path (Sector 18-21): Press Chowk (Madhya Marg) south to Sector 20/21 Chowk
# Ways: 129584355 (rev), 129584356 (rev), 1034047278, 1034047277 (rev), 129478200 (rev), 129478202 (rev)
c7_coords = chain_way_ids([
    (129584355, True),
    (129584356, True),
    (1034047278, False),
    (1034047277, True),
    (129478200, True),
    (129478202, True),
])

# 8. Vigyan Path (Sector 14 Panjab Univ): Panjab University perimeter
# Ways: 129777142 (rev), 129722953 (rev), 1042607575 (rev), 129720775 (rev), 129584371 (rev), 129584414 (rev)
c8_coords = chain_way_ids([
    (129777142, True),
    (129722953, True),
    (1042607575, True),
    (129720775, True),
    (129584371, True),
    (129584414, True),
])

# 9. Sukhna Path (Sector 5-6 Lake Corridor): Approach corridor leading towards Sukhna Lake
# Ways: 1061964643, 129581124, 1043823247, 1213994978, 129581122, 1213994977
c9_coords = chain_way_ids([
    (1061964643, False),
    (129581124, False),
    (1043823247, False),
    (1213994978, False),
    (129581122, False),
    (1213994977, False),
])

# 10. Uttar Marg (Sukhna Lake Promenade): Lake Club & scenic promenade road
# Ways: 1103427160 (rev), 129722952 (rev), 1030701175 (rev), 1030701177 (rev), 1024118134 (rev)
c10_coords = chain_way_ids([
    (1103427160, True),
    (129722952, True),
    (1030701175, True),
    (1030701177, True),
    (1024118134, True),
])

corridors = [
    ("seg_chandigarh_001", "Madhya Marg (Sector 17–18)", c1_coords, 65.0, 0.88, 3, 1, 14),
    ("seg_chandigarh_002", "Dakshin Marg (Sector 22–35)", c2_coords, 88.0, 0.93, 0, 0, 22),
    ("seg_chandigarh_003", "Jan Marg (Sector 9–17)", c3_coords, 38.0, 0.76, 7, 3, 12),
    ("seg_chandigarh_004", "Himalaya Marg (Sector 22–23)", c4_coords, 70.0, 0.81, 1, 1, 11),
    ("seg_chandigarh_005", "Udyog Path (Sector 14–25 Corridor)", c5_coords, 24.0, 0.69, 12, 5, 8),
    ("seg_chandigarh_006", "Purv Marg (Sector 26–27)", c6_coords, 94.0, 0.95, 0, 0, 30),
    ("seg_chandigarh_007", "Sarovar Path (Sector 18–21)", c7_coords, 82.0, 0.90, 1, 0, 16),
    ("seg_chandigarh_008", "Vigyan Path (Sector 14 Panjab Univ)", c8_coords, 86.0, 0.91, 0, 0, 18),
    ("seg_chandigarh_009", "Sukhna Path (Sector 5–6 Lake Corridor)", c9_coords, 96.0, 0.97, 0, 0, 25),
    ("seg_chandigarh_010", "Uttar Marg (Sukhna Lake Promenade)", c10_coords, 58.0, 0.84, 4, 2, 10),
]

features = []
print("Canonical Corridors Summary:")
for sid, name, pts, score, conf, pot, water, obs in corridors:
    span = dist(pts[0], pts[-1]) * 111 # approx km
    print(f"  {sid}: {name} -> {len(pts)} pts, span: {span:.2f} km")
    print(f"     Start: {pts[0]} -> End: {pts[-1]}")
    features.append({
        "type": "Feature",
        "id": sid,
        "geometry": {
            "type": "LineString",
            "coordinates": pts,
        },
        "properties": {
            "segment_id": sid,
            "name": name,
            "condition_score": score,
            "confidence": conf,
            "pothole_count": pot,
            "waterlogging_count": water,
            "observation_count": obs,
        }
    })

geojson_doc = {
    "type": "FeatureCollection",
    "features": features
}

out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "chandigarh_roads_canonical.geojson"))
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(geojson_doc, f, indent=2)

print(f"\nWritten {len(features)} canonical features to {out_path}")
