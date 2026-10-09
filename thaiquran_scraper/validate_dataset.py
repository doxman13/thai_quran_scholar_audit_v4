"""
Validation and Quality Assurance script for ThaiQuran Scraper output.
Verifies canonical Quran verse counts, detects missing verses, checks for empty translations,
and audits footnote coverage.
"""

import csv
import json
import os
import sys

# Canonical Ayah count per Surah (1 to 114)
CANONICAL_AYAH_COUNTS = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109,
    123, 111, 43, 52, 99, 128, 111, 110, 98, 135,
    112, 78, 118, 64, 77, 227, 93, 88, 69, 60,
    34, 30, 73, 54, 45, 83, 182, 88, 75, 85,
    54, 53, 89, 59, 37, 35, 38, 29, 18, 45,
    60, 49, 62, 55, 78, 96, 29, 22, 24, 13,
    14, 11, 11, 18, 12, 12, 30, 52, 52, 44,
    28, 28, 20, 56, 40, 31, 50, 40, 46, 42,
    29, 19, 36, 25, 22, 17, 19, 26, 30, 20,
    15, 21, 11, 8, 8, 19, 5, 8, 8, 11,
    11, 8, 3, 9, 5, 4, 7, 3, 6, 3,
    5, 4, 5, 6
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "quran_thai_by_surah.json")
CSV_PATH = os.path.join(BASE_DIR, "quran_thai.csv")


def validate():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} does not exist. Run scrape_thaiquran.py first.")
        return False

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=" * 60)
    print("THAIQURAN DATASET VALIDATION REPORT")
    print("=" * 60)

    surah_map = {entry["surah_number"]: entry for entry in data}
    total_surahs = len(surah_map)
    total_ayahs = 0
    total_footnotes = 0
    empty_translations = []
    mismatched_counts = []

    for s_idx, expected_count in enumerate(CANONICAL_AYAH_COUNTS, start=1):
        if s_idx not in surah_map:
            continue

        surah = surah_map[s_idx]
        ayahs = surah.get("ayahs", [])
        actual_count = len(ayahs)
        total_ayahs += actual_count

        if actual_count != expected_count:
            mismatched_counts.append((s_idx, expected_count, actual_count))

        for a in ayahs:
            if not a.get("translation"):
                empty_translations.append(a.get("ayah_key"))
            notes = a.get("footnotes", [])
            total_footnotes += len(notes)

    print(f"Surahs present:         {total_surahs} / 114")
    print(f"Total Ayahs present:    {total_ayahs} (Canonical: 6,236)")
    print(f"Total Footnotes logged: {total_footnotes}")
    print(f"Empty Translations:     {len(empty_translations)}")

    if mismatched_counts:
        print("\n[WARNING] Verse count mismatches detected:")
        for s_num, exp, act in mismatched_counts:
            print(f"  - Surah {s_num}: expected {exp}, got {act}")
    else:
        print("\n[PASS] All present surahs match canonical verse counts!")

    if empty_translations:
        print(f"\n[WARNING] Empty translations found in: {empty_translations[:10]}...")
    else:
        print("[PASS] Zero empty translations found.")

    # Validate CSV
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = list(csv.DictReader(f))
        print(f"\nCSV Integrity Check: {len(reader)} rows matching {total_ayahs} Ayahs in JSON.")
        if len(reader) == total_ayahs:
            print("[PASS] JSON and CSV record counts match perfectly.")
        else:
            print(f"[FAIL] Row count mismatch between JSON ({total_ayahs}) and CSV ({len(reader)})")

    print("=" * 60)
    return len(mismatched_counts) == 0 and len(empty_translations) == 0


if __name__ == "__main__":
    validate()
