"""
Comparison and Analysis Tool: ThaiQuran.com vs Baseline Thai Quran Corpus (v3 / Foundation)
Performs lexical matching, orthography analysis, and commentary mapping.
"""

import json
import os
import re
import sys
from difflib import SequenceMatcher
from typing import Any, Dict, List

# Ensure UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

TQ_JSON = os.path.join(BASE_DIR, "quran_thai_by_surah.json")
V3_JSON = os.path.join(PROJECT_DIR, "thai_v3_spacing_improved.json")
STRUCT_JSON = os.path.join(PROJECT_DIR, "quran_foundation_thai_structured.json")


def clean_footnote_markers(text: str) -> str:
    """Removes footnote callout indices like (1), (415) from translation text."""
    clean = re.sub(r"\(\d+\)", "", text)
    clean = re.sub(r"[ \t\r\f\v]+", " ", clean)
    return clean.strip()


def run_comparison(sample_size: int = 10):
    if not os.path.exists(TQ_JSON):
        print(f"Error: {TQ_JSON} not found.")
        return

    # Load ThaiQuran dataset
    with open(TQ_JSON, "r", encoding="utf-8") as f:
        tq_data = json.load(f)
    tq_dict = {ayah["ayah_key"]: ayah for surah in tq_data for ayah in surah.get("ayahs", [])}

    # Load Baseline dataset (v3)
    v3_dict = {}
    if os.path.exists(V3_JSON):
        with open(V3_JSON, "r", encoding="utf-8") as f:
            v3_data = json.load(f)
        for item in v3_data:
            key = f"{item['surah']}:{item['ayah']}"
            v3_dict[key] = item.get("translation", "")
    elif os.path.exists(STRUCT_JSON):
        with open(STRUCT_JSON, "r", encoding="utf-8") as f:
            struct_data = json.load(f)
        for item in struct_data:
            key = f"{item['surah']}:{item['ayah']}"
            v3_dict[key] = item.get("text", "")

    print("=" * 70)
    print("THAIQURAN.COM VS WORKSPACE CORPUS: PRELIMINARY COMPARISON REPORT")
    print("=" * 70)
    print(f"Total Ayahs loaded from ThaiQuran.com: {len(tq_dict)}")
    print(f"Total Ayahs loaded from Baseline v3:   {len(v3_dict)}")

    # Overall similarity and exact match metrics across all 6,236 Ayahs
    exact_matches = 0
    clean_exact_matches = 0
    total_footnotes = 0
    verses_with_footnotes = 0
    similarity_sum = 0.0

    sample_differences = []

    for key, tq_entry in tq_dict.items():
        raw_tq = tq_entry["translation"]
        clean_tq = clean_footnote_markers(raw_tq)
        notes = tq_entry.get("footnotes", [])
        
        if notes:
            verses_with_footnotes += 1
            total_footnotes += len(notes)

        v3_text = v3_dict.get(key, "").strip()

        if raw_tq == v3_text:
            exact_matches += 1

        if clean_tq == v3_text:
            clean_exact_matches += 1

        ratio = SequenceMatcher(None, clean_tq, v3_text).ratio() if v3_text else 0.0
        similarity_sum += ratio

        if ratio < 0.98 and len(sample_differences) < sample_size and v3_text:
            sample_differences.append({
                "key": key,
                "thaiquran_raw": raw_tq,
                "thaiquran_clean": clean_tq,
                "baseline_v3": v3_text,
                "ratio": ratio,
                "footnotes": notes,
            })

    total_count = len(tq_dict)
    avg_similarity = (similarity_sum / total_count) * 100 if total_count else 0.0

    print(f"\n[METRICS ACROSS ALL 6,236 AYAHS]")
    print(f"  * Average String Similarity (after removing footnote markers): {avg_similarity:.2f}%")
    print(f"  * Exact 100% Identical Matches (clean):                        {clean_exact_matches} / {total_count} ({(clean_exact_matches/total_count)*100:.1f}%)")
    print(f"  * Verses Containing Footnotes/Commentary:                      {verses_with_footnotes} / {total_count} ({(verses_with_footnotes/total_count)*100:.1f}%)")
    print(f"  * Total Commentary Footnotes Extracted:                        {total_footnotes}")

    print("\n" + "=" * 70)
    print("SAMPLE DIFFERENCES & COMMENTARY INTEGRATION PREVIEW")
    print("=" * 70)

    for item in sample_differences[:5]:
        print(f"\n--- Ayah {item['key']} (Similarity: {item['ratio']*100:.1f}%) ---")
        print(f"ThaiQuran Clean: {item['thaiquran_clean']}")
        print(f"Baseline v3:     {item['baseline_v3']}")
        if item["footnotes"]:
            print("Commentary Footnotes:")
            for note in item["footnotes"]:
                print(f"  -> {note}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    run_comparison()
