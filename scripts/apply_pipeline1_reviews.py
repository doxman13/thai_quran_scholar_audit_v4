"""
=============================================================================
AUTOMATED SCHOLAR AUDIT REVIEW APPLICATOR & CROSS-PLATFORM SYNCHRONIZER
=============================================================================
Purpose:
  Applies manual reviewer decisions from Pipeline 1 Review Sheet
  (06_pipeline1_theological_scholarship_review.csv) to:
    1. Source of Truth (thai_quran_scholar_audit_v4 master files)
    2. Mobile App (thai-quran-app SQLite DB & JSON assets)
    3. Web App (thai-quran-web JSON assets & Word-by-Word data)

Usage:
  python scripts/apply_pipeline1_reviews.py
=============================================================================
"""

import os
import csv
import json
import sqlite3
import re
import sys
import shutil

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL_FILES_DIR = os.path.join(BASE_DIR, "final_files")
REVIEW_CSV = os.path.join(FINAL_FILES_DIR, "06_pipeline1_theological_scholarship_review.csv")
MASTER_JSON = os.path.join(FINAL_FILES_DIR, "01_thai_quran_translation_v3_master.json")
MASTER_CSV = os.path.join(FINAL_FILES_DIR, "02_thai_quran_translation_v3_master.csv")
AUDIT_LOG_CSV = os.path.join(FINAL_FILES_DIR, "05_thai_translation_fixes_and_audit_log.csv")

APP_DIR = r"H:\gits\thai-quran-app"
WEB_DIR = r"H:\gits\thai-quran-web"

WESTERN_PUNCTUATION_PATTERN = re.compile(r'[\.,\?!:;“”‘’"—\-_/\\#@\$\%\^\&\*]')

def clean_thai_typography(text: str) -> str:
    """Strips western punctuation and standardizes spacing while preserving Phinthu, Maiyamok, and ()"""
    if not text:
        return ""
    # Strip western punctuation
    t = WESTERN_PUNCTUATION_PATTERN.sub('', text)
    # Collapse double spaces
    t = re.sub(r'[ \t]+', ' ', t).strip()
    return t

def main():
    print("=" * 70)
    print("  THAI QURAN SCHOLAR REVIEW APPLICATOR")
    print("=" * 70)

    if not os.path.exists(REVIEW_CSV):
        print(f"Error: Review CSV not found at {REVIEW_CSV}")
        return

    if not os.path.exists(MASTER_JSON):
        print(f"Error: Master JSON not found at {MASTER_JSON}")
        return

    # 1. Load current master dataset
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        master_data = json.load(f)
    
    # Map by "surah:ayah"
    verse_map = {f"{item['surah']}:{item['ayah']}": item for item in master_data}
    print(f"Loaded {len(verse_map)} master verses from {MASTER_JSON}")

    # 2. Read Review Decisions
    approved_changes = []
    with open(REVIEW_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            decision = (row.get("reviewer_decision") or "").strip()
            if not decision:
                continue
            
            s = int(row["surah"])
            a = int(row["ayah"])
            vk = f"{s}:{a}"
            
            # Check decision type
            dec_upper = decision.upper()
            if dec_upper in ["APPROVED", "APPROVE", "ACCEPT", "YES", "TRUE", "1"]:
                new_text = row.get("proposed_thai", "").strip()
            elif dec_upper in ["REJECTED", "REJECT", "NO", "FALSE", "0"]:
                continue
            else:
                # Reviewer provided custom revised Thai text
                new_text = decision
            
            if not new_text:
                continue

            cleaned_new_text = clean_thai_typography(new_text)
            old_text = verse_map[vk]["translation"]
            
            if old_text != cleaned_new_text:
                approved_changes.append({
                    "surah": s,
                    "ayah": a,
                    "verse_key": vk,
                    "old_text": old_text,
                    "new_text": cleaned_new_text,
                    "issue_type": row.get("issue_type", "THEOLOGICAL_REVIEW"),
                    "explanation": row.get("explanation", "")
                })

    print(f"\nFound {len(approved_changes)} approved changes to apply.")
    if not approved_changes:
        print("No pending approved changes found in reviewer_decision column.")
        print("To approve changes, open final_files/06_pipeline1_theological_scholarship_review.csv")
        print("and set 'reviewer_decision' to 'APPROVED' or type custom revised Thai text.")
        return

    # 3. Apply changes to master in-memory dictionary
    for ch in approved_changes:
        vk = ch["verse_key"]
        verse_map[vk]["translation"] = ch["new_text"]
        print(f"  [Ayah {vk}] Applied: {ch['new_text'][:50]}...")

    updated_master_list = list(verse_map.values())

    # 4. Save updated master JSON & CSV
    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(updated_master_list, f, ensure_ascii=False, indent=2)
    print(f"\n[1/5] Saved updated Master JSON: {MASTER_JSON}")

    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["surah", "ayah", "translation"])
        for item in updated_master_list:
            writer.writerow([item["surah"], item["ayah"], item["translation"]])
    print(f"[2/5] Saved updated Master CSV: {MASTER_CSV}")

    # Also update root mirror files
    root_json = os.path.join(BASE_DIR, "thai_v3_spacing_improved.json")
    root_csv = os.path.join(BASE_DIR, "thai_v3_spacing_improved.csv")
    shutil.copy2(MASTER_JSON, root_json)
    shutil.copy2(MASTER_CSV, root_csv)

    # 5. Append to Audit Log CSV
    if os.path.exists(AUDIT_LOG_CSV):
        with open(AUDIT_LOG_CSV, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            for ch in approved_changes:
                writer.writerow([
                    ch["surah"],
                    ch["ayah"],
                    ch["issue_type"],
                    f"[Scholar Review Approved] {ch['explanation']}",
                    "",
                    "",
                    ch["old_text"],
                    ch["new_text"]
                ])
        print(f"[3/5] Appended {len(approved_changes)} entries to Audit Log: {AUDIT_LOG_CSV}")

    # 6. Apply to Mobile App (thai-quran-app)
    if os.path.exists(APP_DIR):
        print(f"\n[4/5] Updating Mobile App ({APP_DIR})...")
        app_json = os.path.join(APP_DIR, "assets", "thai_v3.json")
        app_db = os.path.join(APP_DIR, "assets", "quran_offline.db")
        service_dart = os.path.join(APP_DIR, "lib", "services", "offline_quran_database_service.dart")

        # Update JSON
        app_dict = {f"{it['surah']}:{it['ayah']}": it["translation"] for it in updated_master_list}
        with open(app_json, "w", encoding="utf-8") as f:
            json.dump(app_dict, f, ensure_ascii=False, indent=2)

        # Update SQLite DB & bump PRAGMA user_version
        conn = sqlite3.connect(app_db)
        c = conn.cursor()
        for ch in approved_changes:
            c.execute("UPDATE verses SET translation_th = ? WHERE verse_key = ?", (ch["new_text"], ch["verse_key"]))
        
        c.execute("PRAGMA user_version;")
        current_ver = c.fetchone()[0] or 24
        next_ver = current_ver + 1
        c.execute(f"PRAGMA user_version = {next_ver};")
        conn.commit()
        conn.close()

        # Update Dart service version
        if os.path.exists(service_dart):
            with open(service_dart, "r", encoding="utf-8") as f:
                dart_code = f.read()
            dart_code = re.sub(r'static const int _targetDbVersion = \d+;', f'static const int _targetDbVersion = {next_ver};', dart_code)
            with open(service_dart, "w", encoding="utf-8") as f:
                f.write(dart_code)

        print(f"      - assets/thai_v3.json updated")
        print(f"      - assets/quran_offline.db updated (version bumped to {next_ver})")
        print(f"      - offline_quran_database_service.dart bumped to {next_ver}")

    # 7. Apply to Web App (thai-quran-web)
    if os.path.exists(WEB_DIR):
        print(f"\n[5/5] Updating Web App ({WEB_DIR})...")
        web_json = os.path.join(WEB_DIR, "src", "data", "thai_v3.json")
        web_audit_log = os.path.join(WEB_DIR, "src", "data", "thai_translation_fixes_and_audit_log.csv")
        exporter_script = os.path.join(WEB_DIR, "scripts", "export_db_for_web.py")

        # Update nested web JSON
        web_dict = {}
        for it in updated_master_list:
            s = str(it["surah"])
            a = str(it["ayah"])
            if s not in web_dict:
                web_dict[s] = {"verses": {}}
            web_dict[s]["verses"][a] = it["translation"]
        
        with open(web_json, "w", encoding="utf-8") as f:
            json.dump(web_dict, f, ensure_ascii=False, indent=2)

        if os.path.exists(AUDIT_LOG_CSV):
            shutil.copy2(AUDIT_LOG_CSV, web_audit_log)

        print(f"      - src/data/thai_v3.json updated")
        print(f"      - src/data/thai_translation_fixes_and_audit_log.csv updated")

        # Run web database exporter
        if os.path.exists(exporter_script):
            print("      - Running export_db_for_web.py to re-sync WBW data...")
            os.system(f'python "{exporter_script}"')

        # 8. Sync to Supabase Storage & Remote Content Versions
        env_local_file = os.path.join(WEB_DIR, ".env.local")
        supabase_url = None
        service_role_key = None
        if os.path.exists(env_local_file):
            with open(env_local_file, "r", encoding="utf-8") as env_f:
                for line in env_f:
                    if line.startswith("NEXT_PUBLIC_SUPABASE_URL="):
                        supabase_url = line.strip().split("=", 1)[1]
                    elif line.startswith("SUPABASE_SERVICE_ROLE_KEY="):
                        service_role_key = line.strip().split("=", 1)[1]

        if supabase_url and service_role_key:
            try:
                import requests
                print("\n[6/6] Synchronizing with Supabase Cloud Storage...")
                upload_url = f"{supabase_url}/storage/v1/object/app-content/thai_v3.json"
                upload_headers = {
                    "apikey": service_role_key,
                    "Authorization": f"Bearer {service_role_key}",
                    "Content-Type": "application/json",
                    "x-upsert": "true"
                }
                payload_bytes = json.dumps(web_dict, ensure_ascii=False, indent=2).encode("utf-8")
                resp = requests.post(upload_url, headers=upload_headers, data=payload_bytes)
                if resp.status_code not in [200, 201]:
                    resp = requests.put(upload_url, headers=upload_headers, data=payload_bytes)

                # Update app_content_versions table
                from datetime import datetime, timezone
                now_iso = datetime.now(timezone.utc).isoformat()
                version_str = f"1.1.{len(approved_changes)}"
                db_url = f"{supabase_url}/rest/v1/app_content_versions?content_key=eq.thai_v3"
                requests.patch(db_url, headers={
                    "apikey": service_role_key,
                    "Authorization": f"Bearer {service_role_key}",
                    "Content-Type": "application/json"
                }, json={"version": version_str, "updated_at": now_iso})

                print(f"      - Supabase Storage (app-content/thai_v3.json) updated")
                print(f"      - app_content_versions table bumped to version {version_str}")
            except Exception as e:
                print(f"      - Note: Supabase sync skipped ({e})")

    print("\n" + "=" * 70)
    print("  ALL UPDATES APPLIED & SYNCHRONIZED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()

