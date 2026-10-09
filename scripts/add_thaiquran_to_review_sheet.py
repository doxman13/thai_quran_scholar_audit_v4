"""
=============================================================================
INTEGRATE THAIQURAN.COM VERSES INTO SCHOLAR AUDIT REVIEW CSV
=============================================================================
Fetches the live scholar audit review sheet from Google Sheets:
  https://docs.google.com/spreadsheets/d/1eeM7mrUjsiFmrDhnhCbPQUo8xIeiQQY--t-gBTQMkPY/edit?gid=1856489305
and adds a 'thaiquran_verse' column containing the Thai Quran translation
scraped by thaiquran_scraper/scrape_thaiquran.py for each relevant surah and ayah.

Outputs:
  1. pipeline1_human_review_with_thaiquran.csv (Full updated review sheet)
  2. thaiquran_verse_column_only.csv (Single-column file for 1-click paste into Google Sheets)
  3. Updates pipeline1_human_review.csv and final_files/06_pipeline1_theological_scholarship_review.csv
=============================================================================
"""

import os
import csv
import io
import sys
import requests

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = r"H:\gits\thai_quran_scholar_audit_v4"
TQ_CSV_PATH = os.path.join(BASE_DIR, "thaiquran_scraper", "quran_thai.csv")
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1eeM7mrUjsiFmrDhnhCbPQUo8xIeiQQY--t-gBTQMkPY/export?format=csv&gid=1856489305"

OUT_WITH_TQ = os.path.join(BASE_DIR, "pipeline1_human_review_with_thaiquran.csv")
OUT_COL_ONLY = os.path.join(BASE_DIR, "thaiquran_verse_column_only.csv")
LOCAL_REVIEW_CSV = os.path.join(BASE_DIR, "pipeline1_human_review.csv")
FINAL_REVIEW_CSV = os.path.join(BASE_DIR, "final_files", "06_pipeline1_theological_scholarship_review.csv")
FINAL_HUMAN_CSV = os.path.join(BASE_DIR, "final_files", "pipeline1_human_review.csv")

def main():
    print("=" * 75)
    print("  ADDING THAIQURAN.COM VERSES TO SCHOLAR AUDIT REVIEW CSV")
    print("=" * 75)

    # 1. Load ThaiQuran scraped dataset
    if not os.path.exists(TQ_CSV_PATH):
        print(f"Error: Scraped ThaiQuran CSV not found at {TQ_CSV_PATH}")
        sys.exit(1)

    with open(TQ_CSV_PATH, "r", encoding="utf-8-sig") as f:
        tq_reader = csv.DictReader(f)
        tq_map = {}
        for row in tq_reader:
            key = (int(row["surah"]), int(row["ayah"]))
            tq_map[key] = row["translation"].strip()

    print(f"Loaded {len(tq_map)} verses from {TQ_CSV_PATH}")

    # 2. Fetch live Google Sheet
    print(f"Fetching live Google Sheet from:\n  {SHEET_CSV_URL}")
    resp = requests.get(SHEET_CSV_URL)
    if resp.status_code != 200:
        print(f"Error: Failed to fetch Google Sheet, status code {resp.status_code}")
        sys.exit(1)

    content = resp.content.decode("utf-8")
    raw_rows = list(csv.reader(io.StringIO(content)))
    header = raw_rows[0]
    data_rows = raw_rows[1:]
    print(f"Fetched {len(data_rows)} audit rows from Google Sheet.")
    print(f"Original Header: {header}")

    # 3. Determine column insertion
    # Original columns:
    # 0: surah, 1: ayah, 2: issue_type, 3: explanation, 4: target_phrase,
    # 5: replacement_phrase, 6: guardrail_status, 7: original_thai,
    # 8: proposed_thai, 9: arabic_anchor, 10: malay_anchor, 11: malay_reference,
    # 12: arabic_text, 13: Chareef_reviewer_decision, 14: comments,
    # 15: Nasroh_reviewer_decision, 16: comments
    
    # Place 'thaiquran_verse' right after 'arabic_text' (index 13)
    # This keeps all reference translations grouped together before reviewer decisions.
    insert_idx = 13 if "arabic_text" in header else len(header)

    new_header = header[:insert_idx] + ["thaiquran_verse"] + header[insert_idx:]
    print(f"New Header ({len(new_header)} cols): {new_header}")

    matched_count = 0
    missing_count = 0
    updated_rows = []
    column_only_rows = [["thaiquran_verse"]]

    for r in data_rows:
        s = int(r[0].strip())
        a = int(r[1].strip())
        tq_verse = tq_map.get((s, a), "")

        if tq_verse:
            matched_count += 1
        else:
            missing_count += 1

        new_r = r[:insert_idx] + [tq_verse] + r[insert_idx:]
        updated_rows.append(new_r)
        column_only_rows.append([tq_verse])

    print(f"\nMatching Results:")
    print(f"  Matched: {matched_count} / {len(data_rows)}")
    print(f"  Missing: {missing_count} / {len(data_rows)}")

    # 4. Save pipeline1_human_review_with_thaiquran.csv
    with open(OUT_WITH_TQ, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(new_header)
        writer.writerows(updated_rows)
    print(f"\nSaved updated full CSV to:\n  {OUT_WITH_TQ}")

    # 5. Save thaiquran_verse_column_only.csv
    with open(OUT_COL_ONLY, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(column_only_rows)
    print(f"Saved single-column CSV (for 1-click Google Sheet paste) to:\n  {OUT_COL_ONLY}")

    # 6. Update local repository review files
    for path in [LOCAL_REVIEW_CSV, FINAL_REVIEW_CSV, FINAL_HUMAN_CSV]:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(new_header)
            writer.writerows(updated_rows)
        print(f"Updated repository reference at:\n  {path}")

    # Sample preview
    print("\nSample Preview (First 3 rows):")
    for r in updated_rows[:3]:
        print(f"[{r[0]}:{r[1]}] Original: {r[7][:35]}... | ThaiQuran: {r[insert_idx][:35]}...")

if __name__ == "__main__":
    main()
