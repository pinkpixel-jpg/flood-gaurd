import re
import hashlib
import os
import geopandas as gpd


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()[:12]


def graphml_bounds(p):
    lats = []
    lons = []
    n_nodes = 0
    cur = {}
    lat_re = re.compile(rb'<data key="d4">(-?[\d.]+)</data>')
    lon_re = re.compile(rb'<data key="d5">(-?[\d.]+)</data>')
    with open(p, "rb") as f:
        for line in f:
            if b"<node " in line or line.startswith(b"<node"):
                n_nodes += 1
                continue
            m = lat_re.search(line)
            if m:
                cur["lat"] = float(m.group(1))
                continue
            m = lon_re.search(line)
            if m:
                cur["lon"] = float(m.group(1))
                continue
            if b"</node>" in line:
                if "lat" in cur and "lon" in cur:
                    lats.append(cur["lat"])
                    lons.append(cur["lon"])
                cur = {}
    if not lats:
        return None
    return (min(lons), min(lats), max(lons), max(lats), n_nodes)


STUDY = (73.60, 18.30, 74.10, 18.75)


def covers(b):
    return b[0] <= STUDY[0] and b[1] <= STUDY[1] and b[2] >= STUDY[2] and b[3] >= STUDY[3]


files = [
    ("A_top_city_roads_graphml", r"city_roads\pune_roads.graphml.xml"),
    ("B_hehe_city_roads_graphml", r"hehehackathon\city_roads\pune_roads.graphml.xml"),
    ("C_hehe_pune_roads.graphml", r"hehehackathon\pune_roads.graphml"),
]
for label, p in files:
    if not os.path.exists(p):
        print(label, ": MISSING")
        continue
    print("%s | %.1f MB | md5=%s" % (label, os.path.getsize(p) / 1e6, md5(p)))
    try:
        r = graphml_bounds(p)
        if r:
            print("   nodes=%d | lon %.5f..%.5f | lat %.5f..%.5f | covers FULL study bbox: %s"
                  % (r[4], r[0], r[2], r[1], r[3], covers((r[0], r[1], r[2], r[3]))))
    except Exception as e:
        print("   parse error:", str(e)[:100])

print()
p = r"data\processed\pune_roads.geojson"
g = gpd.read_file(p)
b = g.total_bounds
print("D_processed_pune_roads.geojson | %.1f MB | features=%d | crs=%s"
      % (os.path.getsize(p) / 1e6, len(g), g.crs))
print("   lon %.5f..%.5f | lat %.5f..%.5f | covers FULL study bbox: %s"
      % (b[0], b[2], b[1], b[3], covers((b[0], b[1], b[2], b[3]))))
if "highway" in g.columns:
    print("   highway values:", g["highway"].value_counts().head(8).to_dict())

print()
for lbl, p in [("waterways_raw", r"data\raw\osm\pune_waterways_raw.geojson"),
               ("waterways_proc", r"data\processed\pune_waterways.geojson"),
               ("drainage_proc", r"data\processed\pune_drainage.geojson")]:
    if os.path.exists(p):
        gg = gpd.read_file(p)
        bb = gg.total_bounds
        print("%s | %d feats | lon %.4f..%.4f lat %.4f..%.4f | PRESERVED"
              % (lbl, len(gg), bb[0], bb[2], bb[1], bb[3]))
