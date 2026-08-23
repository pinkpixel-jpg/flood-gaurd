import json
import urllib.request

raw = urllib.request.urlopen(
    "http://localhost:8000/api/zones/PUNE_G001?date=2024-07-15").read().decode()
j = json.loads(raw)
print("keys:", sorted(j.keys()))
print("vulnerability:", "vulnerability" in j, "| river:", "river" in j)
