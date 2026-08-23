import io

path = "frontend/live-map.html"
s = io.open(path, encoding="utf-8").read()

# remove the three decorative extra dot groups (keep exactly one per zone)
extras = [
    '<g class="map-zone risk-low"><circle class="halo" cx="660" cy="150" r="20"/><circle class="core" cx="660" cy="150" r="8"/></g>',
    '<g class="map-zone risk-low"><circle class="halo" cx="450" cy="130" r="20"/><circle class="core" cx="450" cy="130" r="8"/></g>',
    '<g class="map-zone risk-high"><circle class="halo" cx="420" cy="272" r="24"/><circle class="core" cx="420" cy="272" r="11"/></g>',
]
for e in extras:
    s = s.replace(e, "")

# tag the four real zone groups with data-grid
tags = [
    ('<g class="map-zone risk-low"><circle class="halo" cx="180" cy="150" r="20"/>',
     '<g class="map-zone risk-low" data-grid="PUNE_G003"><circle class="halo" cx="180" cy="150" r="20"/>'),
    ('<g class="map-zone risk-med"><circle class="halo" cx="300" cy="300" r="22"/>',
     '<g class="map-zone risk-med" data-grid="PUNE_G001"><circle class="halo" cx="300" cy="300" r="22"/>'),
    ('<g class="map-zone risk-med"><circle class="halo" cx="600" cy="290" r="22"/>',
     '<g class="map-zone risk-med" data-grid="PUNE_G002"><circle class="halo" cx="600" cy="290" r="22"/>'),
    ('<g class="map-zone risk-high"><circle class="halo" cx="560" cy="372" r="24"/>',
     '<g class="map-zone risk-high" data-grid="PUNE_G004"><circle class="halo" cx="560" cy="372" r="24"/>'),
]
for old, new in tags:
    if old in s:
        s = s.replace(old, new)
    elif new.split("><circle")[0] not in s:
        print("WARN missing:", old[:60])

io.open(path, "w", encoding="utf-8").write(s)
print("extras removed | data-grid tags applied")
