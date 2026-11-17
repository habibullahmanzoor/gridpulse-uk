"""Append one snapshot of the GB grid to data/YYYY-MM.jsonl.

Standard library only, so the GitHub Action needs no dependency install.
Source: Carbon Intensity API (National Grid ESO / University of Oxford).
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.carbonintensity.org.uk"
DATA = Path(__file__).resolve().parent.parent / "data"


def get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/json", "User-Agent": "gridpulse-uk-snapshot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["data"]


def main():
    now = datetime.now(timezone.utc)
    cur = get("/intensity")[0]
    gen = get("/generation")
    reg = get("/regional")[0]["regions"]

    record = {
        "ts": now.strftime("%Y-%m-%dT%H:%MZ"),
        "period_from": cur["from"],
        "gb": {
            "forecast": cur["intensity"]["forecast"],
            "actual": cur["intensity"]["actual"],
            "index": cur["intensity"]["index"],
            "mix": {m["fuel"]: m["perc"] for m in gen["generationmix"]},
        },
        "regions": {
            str(r["regionid"]): {
                "name": r["shortname"],
                "forecast": r["intensity"]["forecast"],
                "mix": {m["fuel"]: m["perc"] for m in r["generationmix"]},
            }
            for r in reg
            if r["regionid"] <= 14  # 15-17 are England/Scotland/Wales aggregates
        },
    }

    DATA.mkdir(exist_ok=True)
    out = DATA / f"{now:%Y-%m}.jsonl"
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")
    print(f"wrote {record['ts']} -> {out.name} (GB {record['gb']['forecast']} gCO2/kWh)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # keep the workflow green-or-red honestly
        print("snapshot failed:", e, file=sys.stderr)
        sys.exit(1)
