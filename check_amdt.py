import json
from pathlib import Path

cache_dir = Path(".cache/assemblee_data")
files = sorted(cache_dir.glob("*.json"), key=lambda x: x.stat().st_size, reverse=True)

for f in files[:1]:
    print(f"File: {f.name}")
    print(f"Size: {f.stat().st_size/1024/1024:.0f} MB")

    data = json.load(open(f))
    print(f"Items: {len(data)}")

    # Count sorts
    sorts = {}
    etats = {}

    for item in data:
        if "amendement" not in item:
            continue
        cycle = item["amendement"].get("cycleDeVie", {}) or {}

        sort_data = cycle.get("sort")
        if sort_data and isinstance(sort_data, dict):
            lib = sort_data.get("libelle", "")
            if lib:
                sorts[lib] = sorts.get(lib, 0) + 1

        etat_data = cycle.get("etatDesTraitements", {})
        if isinstance(etat_data, dict):
            etat_data = etat_data.get("etat", {})
        if etat_data and isinstance(etat_data, dict):
            lib = etat_data.get("libelle", "")
            if lib:
                etats[lib] = etats.get(lib, 0) + 1

    print(f"\nSort counts: {sorts}")
    print(f"\nEtat counts: {etats}")
