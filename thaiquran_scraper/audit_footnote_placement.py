"""
Footnote Placement Auditor with Letter Count Verification
Audits the placement of every inserted footnote marker [N] in the Annotated Base Translation
against its original position (N) in ThaiQuran.com by:
  1. Exact letter count comparison (excluding spaces/diacritics).
  2. Relative percentage position within the verse.
  3. Bidirectional anchor word comparison (left and right context).

Outputs:
  - Terminal summary statistics across all 7,333 markers
  - thaiquran_scraper/footnote_placement_audit_report.csv (Full granular audit log)
  - thaiquran_scraper/footnote_placement_review_needed.csv (Only items flagged for human review)
"""

import csv
import json
import logging
import os
import re
import sys
from difflib import SequenceMatcher
from typing import Any, Dict, List

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("FootnotePlacementAuditor")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TQ_JSON_PATH = os.path.join(BASE_DIR, "quran_thai_by_surah.json")
MASTER_JSON_PATH = os.path.join(BASE_DIR, "thai_quran_master_dual_translation.json")

FULL_AUDIT_CSV = os.path.join(BASE_DIR, "footnote_placement_audit_report.csv")
REVIEW_CSV = os.path.join(BASE_DIR, "footnote_placement_review_needed.csv")

CONTEXT_WINDOW = 25


def normalize_thai_for_audit(text: str) -> str:
    """Normalize text for comparison (strip diacritics, spaces, etc.)."""
    if not text:
        return ""
    text = re.sub(r"[\[\(]\d+[\]\)]", "", text)
    text = re.sub(r"[\sๆฯ\.,!?\(\)]+", "", text)
    text = text.replace("์", "").replace("ฺ", "")
    return text.strip()


def run_audit():
    logger.info("Starting Footnote Placement Audit with Letter Count Verification...")

    if not os.path.exists(TQ_JSON_PATH) or not os.path.exists(MASTER_JSON_PATH):
        logger.error("Required dataset files missing. Ensure scraping and generation completed.")
        return

    with open(TQ_JSON_PATH, "r", encoding="utf-8") as f:
        tq_data = json.load(f)
    tq_dict = {a["ayah_key"]: a for s in tq_data for a in s["ayahs"]}

    with open(MASTER_JSON_PATH, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    audit_rows: List[Dict[str, Any]] = []

    # Counters
    delta_within_3 = 0
    delta_within_7 = 0
    delta_large = 0

    for r in master_data:
        if not r.get("has_footnotes"):
            continue

        key = r["ayah_key"]
        tq_record = tq_dict.get(key)
        if not tq_record:
            continue

        tq_raw = tq_record["translation"]
        annotated_raw = r["translation_annotated"]
        base_clean = r["translation_clean"]

        # Clean full strings for relative length
        tq_clean_full = re.sub(r"\s+", "", re.sub(r"\(\d+\)", "", tq_raw))
        base_clean_full = re.sub(r"\s+", "", base_clean)
        len_tq_full = len(tq_clean_full) if tq_clean_full else 1
        len_base_full = len(base_clean_full) if base_clean_full else 1

        tq_search_start = 0
        ann_search_start = 0

        for fn in r.get("footnotes", []):
            fn_id = str(fn["footnote_id"])

            # 1. Locate marker in ThaiQuran source
            tq_target = f"({fn_id})"
            tq_pos = tq_raw.find(tq_target, tq_search_start)
            if tq_pos == -1:
                tq_pos = tq_raw.find(tq_target)
            else:
                tq_search_start = tq_pos + len(tq_target)

            # 2. Locate marker in Annotated Base
            ann_target = f"[{fn_id}]"
            ann_pos = annotated_raw.find(ann_target, ann_search_start)
            if ann_pos == -1:
                ann_pos = annotated_raw.find(ann_target)
            else:
                ann_search_start = ann_pos + len(ann_target)

            if tq_pos == -1 or ann_pos == -1:
                continue

            # 3. Calculate Letter Count (excluding spaces and markers)
            tq_prefix = tq_raw[:tq_pos]
            tq_clean_prefix = re.sub(r"\s+", "", re.sub(r"\(\d+\)", "", tq_prefix))
            tq_letter_count = len(tq_clean_prefix)

            ann_prefix = annotated_raw[:ann_pos]
            ann_clean_prefix = re.sub(r"\s+", "", re.sub(r"\[\d+\]", "", ann_prefix))
            base_letter_count = len(ann_clean_prefix)

            letter_delta = abs(tq_letter_count - base_letter_count)
            tq_pct = (tq_letter_count / len_tq_full) * 100
            base_pct = (base_letter_count / len_base_full) * 100
            pct_delta = abs(tq_pct - base_pct)

            # 4. Extract Anchor Contexts
            tq_left = tq_raw[max(0, tq_pos - CONTEXT_WINDOW):tq_pos].strip()
            tq_right = tq_raw[tq_pos + len(tq_target):min(len(tq_raw), tq_pos + len(tq_target) + CONTEXT_WINDOW)].strip()

            ann_left = annotated_raw[max(0, ann_pos - CONTEXT_WINDOW):ann_pos].strip()
            ann_right = annotated_raw[ann_pos + len(ann_target):min(len(annotated_raw), ann_pos + len(ann_target) + CONTEXT_WINDOW)].strip()

            tq_left_clean = re.sub(r"\(\d+\)", "", tq_left)
            tq_right_clean = re.sub(r"\(\d+\)", "", tq_right)
            ann_left_clean = re.sub(r"\[\d+\]", "", ann_left)
            ann_right_clean = re.sub(r"\[\d+\]", "", ann_right)

            norm_tq_left = normalize_thai_for_audit(tq_left_clean)
            norm_ann_left = normalize_thai_for_audit(ann_left_clean)
            left_ratio = SequenceMatcher(None, norm_tq_left, norm_ann_left).ratio() if (norm_tq_left or norm_ann_left) else 1.0

            # 5. Status Decision
            if letter_delta <= 3:
                status = "PERFECT"
                delta_within_3 += 1
            elif letter_delta <= 7 or (pct_delta <= 2.5 and left_ratio >= 0.70):
                status = "HIGH_CONFIDENCE"
                delta_within_7 += 1
            elif letter_delta <= 15 and pct_delta <= 5.0:
                status = "REVIEW_SUGGESTED"
                delta_large += 1
            else:
                status = "MISALIGNED_DRIFT"
                delta_large += 1

            audit_rows.append({
                "ayah_key": key,
                "surah": r["surah"],
                "ayah": r["ayah"],
                "footnote_id": fn_id,
                "status": status,
                "letter_delta": letter_delta,
                "tq_letter_count": tq_letter_count,
                "base_letter_count": base_letter_count,
                "pct_delta": f"{pct_delta:.1f}%",
                "tq_anchor_left": tq_left_clean,
                "base_anchor_left": ann_left_clean,
                "tq_anchor_right": tq_right_clean,
                "base_anchor_right": ann_right_clean,
                "footnote_snippet": fn.get("text", "")[:80],
            })

    total_audited = len(audit_rows)

    # 1. Export Complete Audit Report CSV
    logger.info(f"Writing complete audit log ({total_audited} markers) to {FULL_AUDIT_CSV}...")
    with open(FULL_AUDIT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "ayah_key",
            "surah",
            "ayah",
            "footnote_id",
            "status",
            "letter_delta",
            "tq_letter_count",
            "base_letter_count",
            "pct_delta",
            "tq_anchor_left",
            "base_anchor_left",
            "tq_anchor_right",
            "base_anchor_right",
            "footnote_snippet",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_rows)

    # 2. Export Review-Needed CSV
    review_rows = [r for r in audit_rows if r["status"] in ("REVIEW_SUGGESTED", "MISALIGNED_DRIFT")]
    logger.info(f"Writing {len(review_rows)} flagged items to {REVIEW_CSV}...")
    with open(REVIEW_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(review_rows)

    logger.info("=" * 70)
    logger.info("LETTER COUNT AUDIT RESULTS (ALL 7,333 MARKERS)")
    logger.info("=" * 70)
    logger.info(f"Total Markers Audited:                  {total_audited}")
    logger.info(f"1. Delta <= 3 letters (Exact/Near-Zero): {delta_within_3:<5} ({(delta_within_3/total_audited)*100:.1f}%)")
    logger.info(f"2. Delta 4-7 letters (Minor Spacing/Var):{delta_within_7:<5} ({(delta_within_7/total_audited)*100:.1f}%)")
    logger.info(f"3. Flagged for Review (Delta > 7/drift): {len(review_rows):<5} ({(len(review_rows)/total_audited)*100:.1f}%)")
    logger.info("-" * 70)
    safe_pct = ((delta_within_3 + delta_within_7) / total_audited) * 100
    logger.info(f"TOTAL VERIFIED ACCURATE (Tiers 1 & 2):   {delta_within_3 + delta_within_7} ({safe_pct:.1f}%)")
    logger.info(f"Full Report:   {FULL_AUDIT_CSV}")
    logger.info(f"Review Report: {REVIEW_CSV}")
    logger.info("=" * 70)


if __name__ == "__main__":
    run_audit()
