#!/usr/bin/env python3
"""Collects the online signature counts of the ECI "Rights for Nature" from the
European Commission's public register API and appends them to CSV files.

Only uses the Python standard library, so nothing needs to be installed.
"""
import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

URL = "https://register.eci.ec.europa.eu/core/api/register/details/2026/000006"
OUT_DIR = os.environ.get("ECI_OUT_DIR", ".")
TOTALS_CSV = os.path.join(OUT_DIR, "totals.csv")
COUNTRIES_CSV = os.path.join(OUT_DIR, "countries.csv")


def fetch():
    req = urllib.request.Request(
        URL,
        headers={
            "User-Agent": "RightsForNature-ECI-monitor/1.0 (hourly, non-commercial)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def last_update_in_file():
    if not os.path.exists(TOTALS_CSV):
        return None
    with open(TOTALS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-1]["ec_update"] if rows else None


def main():
    status, data = fetch()
    sos = data.get("sosReport")
    if not sos:
        sys.exit("ERROR: 'sosReport' not found in response. The API may have changed.")

    total = sos["totalSignatures"]
    ec_update = sos["onlineSosUpdateDate"]
    entries = sos["entry"]

    if sum(e["total"] for e in entries) != total:
        print("WARNING: country figures do not add up to the total.")

    print(f"HTTP {status} | total {total} | EC update {ec_update} | {len(entries)} countries")

    if ec_update == last_update_in_file():
        print("No new EC update since last run, nothing stored.")
        return

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new_file = not os.path.exists(TOTALS_CSV)
    with open(TOTALS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["collected_utc", "ec_update", "total"])
        w.writerow([now, ec_update, total])

    new_file = not os.path.exists(COUNTRIES_CSV)
    with open(COUNTRIES_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["collected_utc", "ec_update", "country", "total"])
        for e in sorted(entries, key=lambda x: x["countryCodeType"]):
            w.writerow([now, ec_update, e["countryCodeType"], e["total"]])
    print("Stored.")


if __name__ == "__main__":
    main()
