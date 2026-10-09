"""
Generate Verse-Indexed Footnote Deliverables
Transforms cumulative running footnote numbers [18], [19], [471]
into clean per-verse relative indices [1], [2], [3]...
while preserving original_tq_id for reference and traceability.

Saves into separate dedicated files:
  - thaiquran_scraper/thai_quran_master_verse_indexed.json
  - thaiquran_scraper/thai_quran_master_verse_indexed.csv
  - thaiquran_scraper/quran_footnotes_verse_indexed.json
"""

import csv
import json
import logging
import os
import re
import sys
from typing import Any, Dict, List

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("VerseIndexGenerator")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_MASTER_JSON = os.path.join(BASE_DIR, "thai_quran_master_dual_translation.json")

OUT_MASTER_JSON = os.path.join(BASE_DIR, "thai_quran_master_verse_indexed.json")
OUT_MASTER_CSV = os.path.join(BASE_DIR, "thai_quran_master_verse_indexed.csv")
OUT_FOOTNOTES_JSON = os.path.join(BASE_DIR, "quran_footnotes_verse_indexed.json")


def convert_to_verse_indexed():
    logger.info("=" * 70)
    logger.info("Starting Verse-Indexed Dataset Generation...")
    logger.info("=" * 70)

    if not os.path.exists(SOURCE_MASTER_JSON):
        logger.error(f"Source file not found: {SOURCE_MASTER_JSON}")
        return

    with open(SOURCE_MASTER_JSON, "r", encoding="utf-8") as f:
        source_records: List[Dict[str, Any]] = json.load(f)

    new_master_records = []
    new_footnotes_library = {}

    total_verses = len(source_records)
    total_notes_converted = 0
    verses_with_notes = 0

    for item in source_records:
        surah = item["surah"]
        ayah = item["ayah"]
        key = item["ayah_key"]
        clean_text = item["translation_clean"]
        old_annotated = item["translation_annotated"]
        old_notes = item.get("footnotes", [])

        if not old_notes:
            new_master_records.append({
                "surah": surah,
                "ayah": ayah,
                "ayah_key": key,
                "translation_clean": clean_text,
                "translation_annotated": clean_text,
                "has_footnotes": False,
                "footnote_count": 0,
                "footnotes": [],
            })
            continue

        verses_with_notes += 1
        counter = 0
        new_notes_list = []

        # Find all old markers in order of appearance
        def replacer(match):
            nonlocal counter
            counter += 1
            return f"[{counter}]"

        new_annotated = re.sub(r"\[\d+\]", replacer, old_annotated)

        for idx, old_fn in enumerate(old_notes, start=1):
            new_notes_list.append({
                "footnote_id": idx,
                "original_tq_id": old_fn["footnote_id"],
                "marker": f"[{idx}]",
                "text": old_fn["text"],
            })
            total_notes_converted += 1

        new_master_records.append({
            "surah": surah,
            "ayah": ayah,
            "ayah_key": key,
            "translation_clean": clean_text,
            "translation_annotated": new_annotated,
            "has_footnotes": True,
            "footnote_count": len(new_notes_list),
            "footnotes": new_notes_list,
        })

        new_footnotes_library[key] = new_notes_list

    # 1. Save JSON Master
    logger.info(f"Saving verse-indexed JSON to {OUT_MASTER_JSON}...")
    with open(OUT_MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(new_master_records, f, ensure_ascii=False, indent=2)

    # 2. Save CSV Master
    logger.info(f"Saving verse-indexed CSV to {OUT_MASTER_CSV}...")
    with open(OUT_MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "surah",
            "ayah",
            "ayah_key",
            "translation_clean",
            "translation_annotated",
            "has_footnotes",
            "footnote_count",
            "footnotes",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in new_master_records:
            formatted_notes = " | ".join(
                [f"[{n['footnote_id']}] (orig:{n['original_tq_id']}) {n['text']}" for n in r["footnotes"]]
            )
            writer.writerow({
                "surah": r["surah"],
                "ayah": r["ayah"],
                "ayah_key": r["ayah_key"],
                "translation_clean": r["translation_clean"],
                "translation_annotated": r["translation_annotated"],
                "has_footnotes": r["has_footnotes"],
                "footnote_count": r["footnote_count"],
                "footnotes": formatted_notes,
            })

    # 3. Save Footnotes Lookup JSON
    logger.info(f"Saving verse-indexed footnotes library to {OUT_FOOTNOTES_JSON}...")
    with open(OUT_FOOTNOTES_JSON, "w", encoding="utf-8") as f:
        json.dump(new_footnotes_library, f, ensure_ascii=False, indent=2)

    logger.info("=" * 70)
    logger.info("VERSE-INDEXED DATA GENERATION COMPLETE")
    logger.info(f"Total Ayahs processed:         {total_verses} / 6,236")
    logger.info(f"Verses with Footnotes:         {verses_with_notes}")
    logger.info(f"Total Footnote Markers:        {total_notes_converted}")
    logger.info(f"Output Master JSON:            {OUT_MASTER_JSON}")
    logger.info(f"Output Master CSV:             {OUT_MASTER_CSV}")
    logger.info(f"Output Footnotes JSON:         {OUT_FOOTNOTES_JSON}")
    logger.info("=" * 70)


if __name__ == "__main__":
    convert_to_verse_indexed()
