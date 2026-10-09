"""
Bidirectional N-Gram Master Thai Quran Dataset Generator
Uses Thai Character N-Gram Anchors (Bidirectional Left & Right)
with Letter-Count Disambiguation and Word-Boundary Protection.

Base Text: final_files/01_thai_quran_translation_v3_master.json (Live Master Version)
Footnotes: thaiquran_scraper/quran_thai_by_surah.json
"""

import csv
import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Tuple

# Ensure UTF-8 console output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("BidirectionalMasterGenerator")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

TQ_JSON_PATH = os.path.join(BASE_DIR, "quran_thai_by_surah.json")
BASE_V3_PATH = os.path.join(PROJECT_DIR, "final_files", "01_thai_quran_translation_v3_master.json")

OUTPUT_MASTER_JSON = os.path.join(BASE_DIR, "thai_quran_master_dual_translation.json")
OUTPUT_MASTER_CSV = os.path.join(BASE_DIR, "thai_quran_master_dual_translation.csv")
OUTPUT_FOOTNOTES_JSON = os.path.join(BASE_DIR, "quran_footnotes_library.json")


def clean_footnote_text(raw_note: str) -> str:
    """Strips leading footnote index markers like (1), ((10), etc."""
    cleaned = re.sub(r"^\(+(\d+)\)+\s*", "", raw_note)
    return cleaned.strip()


def normalize_token(s: str) -> str:
    """Normalize word for comparison (strip diacritics, spaces, etc.)."""
    s = re.sub(r"[\[\(]\d+[\]\)]", "", s)
    s = re.sub(r"[\sๆฯ\.,!?\(\)\-:;]+", "", s)
    s = s.replace("์", "").replace("ฺ", "")
    return s.strip()


def build_footnote_pool(tq_data: List[Dict[str, Any]]) -> Dict[int, Dict[str, str]]:
    """Builds a comprehensive pool of all footnotes indexed by surah and footnote number."""
    pool: Dict[int, Dict[str, str]] = {}
    for surah in tq_data:
        s_num = surah["surah_number"]
        pool[s_num] = {}
        for ayah in surah["ayahs"]:
            for note in ayah.get("footnotes", []):
                m = re.match(r"^\(+(\d+)\)+", note)
                if m:
                    fn_id = m.group(1)
                    pool[s_num][fn_id] = clean_footnote_text(note)
    return pool


def build_char_letter_maps(text: str) -> Tuple[List[int], Dict[int, int]]:
    """
    Builds bidirectional mappings:
      1. char_to_letter[char_idx] = count of non-space letters before char_idx
      2. letter_to_char[letter_idx] = character offset in text
    """
    char_to_letter = []
    letter_to_char = {}
    l_count = 0
    for char_idx, ch in enumerate(text):
        char_to_letter.append(l_count)
        if l_count not in letter_to_char:
            letter_to_char[l_count] = char_idx
        if not ch.isspace():
            l_count += 1
    char_to_letter.append(l_count)
    letter_to_char[l_count] = len(text)
    return char_to_letter, letter_to_char


COMBINING_MARKS = set('\u0E31\u0E34\u0E35\u0E36\u0E37\u0E38\u0E39\u0E3A\u0E47\u0E48\u0E49\u0E4A\u0E4B\u0E4C\u0E4D\u0E4E')

VERIFIED_PDF_OVERRIDES = {
    "2:271": {
        "471": "มันก็เป็นสิ่งที่ดีอยู่",
        "472": "มันก็เป็นสิ่งที่ดีแก่พวกเจ้ายิ่งกว่า",
        "473": "ซึ่งบางส่วนจากบรรดาความผิดของพวกเจ้า",
    },
    "4:127": {
        "307": "ในเรื่องของบรรดาหญิง",
        "308": "ซึ่งอยู่ในคัมภีร์นั้น",
        "309": "ซึ่งสิ่งที่ถูกกำหนดขึ้นแก่พวกนาง",
        "310": "จะแต่งงานกับพวกนาง",
        "311": "ในหมู่เด็ก ๆ",
    }
}

def post_process_pos(text: str, pos: int) -> int:
    """Never split Thai combining marks (karan, phinthu, vowels) or parentheses."""
    while pos < len(text) and text[pos] in COMBINING_MARKS:
        pos += 1
    if pos < len(text) and text[pos] in ")]\"'":
        pos += 1
    return pos

def snap_to_word_boundary(text: str, pos: int) -> int:
    """If pos lands inside a non-space Thai word, snaps to the nearest space or boundary."""
    if pos <= 0:
        return 0
    if pos >= len(text):
        return len(text)
    pos = post_process_pos(text, pos)
    if text[pos].isspace() or text[pos-1].isspace() or text[pos] in ".,!?:;)]":
        return pos
    left_space = text.rfind(" ", max(0, pos - 8), pos)
    right_space = text.find(" ", pos, min(len(text), pos + 8))
    if left_space != -1 and (right_space == -1 or (pos - left_space <= right_space - pos)):
        return post_process_pos(text, left_space)
    elif right_space != -1:
        return post_process_pos(text, right_space)
    return pos


def align_markers_ngram(
    tq_text: str,
    base_text: str,
    ayah_key: str,
) -> Tuple[str, List[Tuple[int, str, int]]]:
    """
    Places footnote markers into base_text using character n-gram bidirectional matching
    and letter count disambiguation.
    """
    matches = list(re.finditer(r"\((\d+)\)", tq_text))
    if not matches:
        return base_text, []

    tq_clean_full = re.sub(r"\s+", "", re.sub(r"\(\d+\)", "", tq_text))
    base_clean_full = re.sub(r"\s+", "", base_text)

    char_to_letter, letter_to_char = build_char_letter_maps(base_text)
    total_base_letters = char_to_letter[-1]
    total_tq_letters = len(tq_clean_full)

    placements = []
    last_placed_char_pos = 0

    # Check verified PDF manual overrides first
    overrides = VERIFIED_PDF_OVERRIDES.get(ayah_key)

    for m in matches:
        m_id = m.group(1)
        tq_prefix = tq_text[:m.start()]
        tq_letters = len(re.sub(r"\s+", "", re.sub(r"\(\d+\)", "", tq_prefix)))

        if overrides and m_id in overrides:
            target_phrase = overrides[m_id]
            pos_found = base_text.find(target_phrase)
            if pos_found != -1:
                chosen_pos = post_process_pos(base_text, pos_found + len(target_phrase))
                delta = abs(tq_letters - char_to_letter[chosen_pos])
                placements.append((chosen_pos, m_id, delta))
                last_placed_char_pos = chosen_pos
                continue

        # Rule 1: End-of-verse detection
        tq_after = tq_text[m.end():].strip()
        if not tq_after or re.match(r"^[\s\.,!?]+$", tq_after):
            base_pos = len(base_text)
            delta = abs(tq_letters - total_base_letters)
            placements.append((base_pos, m_id, delta))
            last_placed_char_pos = base_pos
            continue

        # Extract Left and Right Character N-Grams (8-10 chars)
        tq_clean_before = re.sub(r"\(\d+\)", "", tq_prefix).rstrip()
        left_ngram = tq_clean_before[-10:].strip() if len(tq_clean_before) >= 10 else tq_clean_before.strip()
        norm_left = normalize_token(left_ngram)

        tq_clean_after = re.sub(r"\(\d+\)", "", tq_after).lstrip()
        right_ngram = tq_clean_after[:10].strip() if len(tq_clean_after) >= 10 else tq_clean_after.strip()
        norm_right = normalize_token(right_ngram)

        left_candidates = []
        right_candidates = []

        # 1. Search Left N-Gram Candidates (near tq_letters)
        for n_len in [10, 8, 6]:
            sub_left = norm_left[-n_len:] if len(norm_left) >= n_len else norm_left
            if len(sub_left) >= 4:
                for i in range(len(base_text) - len(sub_left) + 1):
                    cand = base_text[i:i + len(sub_left)]
                    if normalize_token(cand) == sub_left:
                        end_pos = post_process_pos(base_text, i + len(sub_left))
                        if end_pos >= last_placed_char_pos:
                            b_letters = char_to_letter[end_pos]
                            d = abs(tq_letters - b_letters)
                            left_candidates.append((d, end_pos))
            if left_candidates:
                break

        # 2. Search Right N-Gram Candidates (near tq_letters)
        for n_len in [10, 8, 6]:
            sub_right = norm_right[:n_len] if len(norm_right) >= n_len else norm_right
            if len(sub_right) >= 4:
                for i in range(len(base_text) - len(sub_right) + 1):
                    cand = base_text[i:i + len(sub_right)]
                    if normalize_token(cand) == sub_right:
                        pos = i
                        while pos > 0 and base_text[pos - 1].isspace():
                            pos -= 1
                        pos = post_process_pos(base_text, pos)
                        if pos >= last_placed_char_pos:
                            b_letters = char_to_letter[pos]
                            d = abs(tq_letters - b_letters)
                            right_candidates.append((d, pos))
            if right_candidates:
                break

        # Decision
        chosen_pos = None
        chosen_delta = float("inf")

        if left_candidates:
            left_candidates.sort(key=lambda x: x[0])
            best_l_delta, best_l_pos = left_candidates[0]
            if best_l_delta <= 7:
                chosen_pos = best_l_pos
                chosen_delta = best_l_delta

        if right_candidates and (chosen_pos is None or chosen_delta > 5):
            right_candidates.sort(key=lambda x: x[0])
            best_r_delta, best_r_pos = right_candidates[0]
            if best_r_delta < chosen_delta:
                chosen_pos = best_r_pos
                chosen_delta = best_r_delta

        if chosen_pos is None:
            combined = left_candidates + right_candidates
            if combined:
                combined.sort(key=lambda x: x[0])
                if combined[0][0] <= 15:
                    chosen_delta, chosen_pos = combined[0]

        # Fallback to Proportional Projection with Word-Boundary Snapping
        if chosen_pos is None:
            ratio = total_base_letters / total_tq_letters if total_tq_letters else 1.0
            target_base_letters = min(total_base_letters, int(round(tq_letters * ratio)))
            target_char_pos = letter_to_char.get(target_base_letters, len(base_text))
            target_char_pos = snap_to_word_boundary(base_text, target_char_pos)
            if target_char_pos < last_placed_char_pos:
                target_char_pos = last_placed_char_pos
            chosen_pos = target_char_pos
            chosen_delta = abs(tq_letters - char_to_letter[chosen_pos])

        chosen_pos = post_process_pos(base_text, chosen_pos)
        placements.append((chosen_pos, m_id, chosen_delta))
        last_placed_char_pos = chosen_pos

    sorted_placements = sorted(
        enumerate(placements),
        key=lambda x: (x[1][0], x[0]),
        reverse=True,
    )

    ann_chars = list(base_text)
    for orig_idx, (pos, m_id, delta) in sorted_placements:
        ann_chars.insert(pos, f"[{m_id}]")

    return "".join(ann_chars), placements


def generate_master():
    logger.info("=" * 70)
    logger.info("Starting Bidirectional N-Gram Master Dataset Generation...")
    logger.info("=" * 70)

    if not os.path.exists(TQ_JSON_PATH) or not os.path.exists(BASE_V3_PATH):
        logger.error("Missing required source files.")
        return

    with open(TQ_JSON_PATH, "r", encoding="utf-8") as f:
        tq_data = json.load(f)

    with open(BASE_V3_PATH, "r", encoding="utf-8") as f:
        base_v3_list = json.load(f)
    base_dict = {f"{item['surah']}:{item['ayah']}": item["translation"] for item in base_v3_list}

    notes_pool = build_footnote_pool(tq_data)

    total_markers_placed = 0
    verses_with_footnotes = 0
    master_records: List[Dict[str, Any]] = []
    footnotes_library: Dict[str, List[Dict[str, Any]]] = {}

    for surah_obj in tq_data:
        s_num = surah_obj["surah_number"]
        for ayah_obj in surah_obj["ayahs"]:
            a_num = ayah_obj["ayah_number"]
            key = ayah_obj["ayah_key"]
            tq_text = ayah_obj["translation"]
            clean_base_text = base_dict.get(key, "").strip()

            annotated_text, placements = align_markers_ngram(
                tq_text=tq_text,
                base_text=clean_base_text,
                ayah_key=key,
            )

            if not placements:
                master_records.append({
                    "surah": s_num,
                    "ayah": a_num,
                    "ayah_key": key,
                    "translation_clean": clean_base_text,
                    "translation_annotated": clean_base_text,
                    "has_footnotes": False,
                    "footnote_count": 0,
                    "footnotes": [],
                })
                continue

            verses_with_footnotes += 1
            total_markers_placed += len(placements)

            verse_footnotes = []
            for _, m_id, _ in placements:
                fn_text = notes_pool.get(s_num, {}).get(m_id, "")
                verse_footnotes.append({
                    "footnote_id": int(m_id),
                    "marker": f"[{m_id}]",
                    "text": fn_text,
                })

            master_records.append({
                "surah": s_num,
                "ayah": a_num,
                "ayah_key": key,
                "translation_clean": clean_base_text,
                "translation_annotated": annotated_text,
                "has_footnotes": True,
                "footnote_count": len(verse_footnotes),
                "footnotes": verse_footnotes,
            })

            footnotes_library[key] = verse_footnotes

    master_records.sort(key=lambda r: (r["surah"], r["ayah"]))

    # 1. Export Master JSON
    logger.info(f"Writing {len(master_records)} master records to {OUTPUT_MASTER_JSON}...")
    with open(OUTPUT_MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(master_records, f, ensure_ascii=False, indent=2)

    # 2. Export Master CSV
    logger.info(f"Writing {len(master_records)} master records to {OUTPUT_MASTER_CSV}...")
    with open(OUTPUT_MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
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
        for r in master_records:
            formatted_notes = " | ".join(
                [f"[{n['footnote_id']}] {n['text']}" for n in r["footnotes"]]
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

    # 3. Export Footnotes Library JSON
    logger.info(f"Writing standalone footnotes library to {OUTPUT_FOOTNOTES_JSON}...")
    with open(OUTPUT_FOOTNOTES_JSON, "w", encoding="utf-8") as f:
        json.dump(footnotes_library, f, ensure_ascii=False, indent=2)

    logger.info("=" * 70)
    logger.info("BIDIRECTIONAL N-GRAM GENERATION COMPLETE")
    logger.info(f"Total Ayahs processed:           {len(master_records)} / 6,236")
    logger.info(f"Verses with Footnotes:           {verses_with_footnotes} ({(verses_with_footnotes/len(master_records))*100:.1f}%)")
    logger.info(f"Total Footnote Markers placed:   {total_markers_placed}")
    logger.info(f"Master JSON:      {OUTPUT_MASTER_JSON}")
    logger.info(f"Master CSV:       {OUTPUT_MASTER_CSV}")
    logger.info(f"Footnotes Lookup: {OUTPUT_FOOTNOTES_JSON}")
    logger.info("=" * 70)


if __name__ == "__main__":
    generate_master()
