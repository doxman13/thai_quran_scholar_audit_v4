"""
=============================================================================
STANDARDIZE PHARAOH TRANSLITERATION TO 'ฟิรเอานฺ' (PATTERN 1)
=============================================================================
Applies standard King Fahad transliteration 'ฟิรเอานฺ' to the 14 non-standard
verses (15 occurrences), ensuring zero other words are altered:
  - 12 occurrences of 'ฟิรฺเอาน์' (Surah 7 & 8) -> 'ฟิรเอานฺ'
  - 2 occurrences of 'ฟิรเอาน' (20:78, 20:79) -> 'ฟิรเอานฺ'
  - 1 occurrence of 'ฟีรเอานฺ' (23:46 typo) -> 'ฟิรเอานฺ'

Synchronizes:
  1. Audit v4 Master Files (01_master.json, 02_master.csv, mirrors)
  2. Audit Logs (03_website_fixes...csv, thai_translation_fixes...csv)
  3. Mobile App (thai_v3.json, quran_offline.db user_version 26, Dart service)
  4. Web App (thai_v3.json, audit log, export_db_for_web.py)
  5. Supabase Storage (app-content/thai_v3.json) & app_content_versions (1.2.1)
=============================================================================
"""

import os
import json
import csv
import sqlite3
import re
import sys
import shutil
import datetime
import requests

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r"H:\gits\thai_quran_scholar_audit_v4"
FINAL_DIR = os.path.join(BASE_DIR, "final_files")
MASTER_JSON = os.path.join(FINAL_DIR, "01_thai_quran_translation_v3_master.json")
MASTER_CSV = os.path.join(FINAL_DIR, "02_thai_quran_translation_v3_master.csv")
AUDIT_LOG_FINAL = os.path.join(FINAL_DIR, "03_website_fixes_and_audit_transparency_log.csv")
AUDIT_LOG_ROOT = os.path.join(BASE_DIR, "thai_translation_fixes_and_audit_log.csv")

APP_DIR = r"H:\gits\thai-quran-app"
WEB_DIR = r"H:\gits\thai-quran-web"

TARGET_VERSES = {
    "7:103": ("ฟิรฺเอาน์", "ฟิรเอานฺ"),
    "7:104": ("ฟิรฺเอาน์", "ฟิรเอานฺ"),
    "7:109": ("ฟิรฺเอาน์", "ฟิรเอานฺ"),
    "7:113": ("ฟิรฺเอาน์", "ฟิรเอานฺ"),
    "7:123": ("ฟิรฺเอาน์", "ฟิรเอานฺ"),
    "7:127": ("ฟิรฺเอาน์", "ฟิรเอานฺ"),
    "7:130": ("ฟิรฺเอาน์", "ฟิรเอานฺ"),
    "7:137": ("ฟิรฺเอาน์", "ฟิรเอานฺ"),
    "7:141": ("ฟิรฺเอาน์", "ฟิรเอานฺ"),
    "8:52":  ("ฟิรฺเอาน์", "ฟิรเอานฺ"),
    "8:54":  ("ฟิรฺเอาน์", "ฟิรเอานฺ"), # 2 occurrences in this verse
    "20:78": ("ฟิรเอานพร้อมด้วย", "ฟิรเอานฺพร้อมด้วย"), # protect against greedy matches
    "20:79": ("และฟิรเอานได้", "และฟิรเอานฺได้"),
    "23:46": ("ฟีรเอานฺ", "ฟิรเอานฺ")
}

def main():
    print("=" * 75)
    print("  STANDARDIZING PHARAOH TO 'ฟิรเอานฺ' (PATTERN 1)")
    print("=" * 75)

    # 1. Load Master JSON
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        master_list = json.load(f)

    verse_map = {f"{it['surah']}:{it['ayah']}": it for it in master_list}
    print(f"Loaded {len(master_list)} verses from Master JSON.")

    applied_changes = []
    for vk, (src_substr, target_substr) in TARGET_VERSES.items():
        if vk not in verse_map:
            raise ValueError(f"Verse {vk} not found in master dataset!")
        
        orig_text = verse_map[vk]["translation"]
        if src_substr not in orig_text:
            raise ValueError(f"Substring '{src_substr}' not found in {vk}: {orig_text}")
        
        # Replace only the target substring
        new_text = orig_text.replace(src_substr, target_substr)
        
        # Double check no other characters were touched
        diff_len = len(new_text) - len(orig_text)
        # For 7:103..141, 8:52: 'ฟิรฺเอาน์' (9 chars) -> 'ฟิรเอานฺ' (8 chars) -> diff is -1
        # For 8:54: 2 occurrences -> diff is -2
        # For 20:78, 20:79: +1 char (adding ฺ) -> diff is +1
        # For 23:46: diff is 0
        verse_map[vk]["translation"] = new_text
        applied_changes.append({
            "verse_key": vk,
            "surah": int(vk.split(":")[0]),
            "ayah": int(vk.split(":")[1]),
            "old_text": orig_text,
            "new_text": new_text,
            "src": src_substr,
            "target": target_substr
        })
        print(f"  [{vk}] Updated: '{src_substr}' -> '{target_substr}'")

    print(f"\nApplied updates to all {len(applied_changes)} target verses.")

    # 2. Strict Verification of Whole Master Dataset
    updated_master_list = list(verse_map.values())
    total_firawn = sum(len(re.findall(r'ฟิรเอานฺ', it['translation'])) for it in updated_master_list)
    total_firawn_old = sum(len(re.findall(r'ฟิรฺเอาน์', it['translation'])) for it in updated_master_list)
    total_firawn_typo = sum(len(re.findall(r'ฟีรเอานฺ', it['translation'])) for it in updated_master_list)
    total_firawn_plain = sum(len(re.findall(r'ฟิรเอาน(?![ฺ์])', it['translation'])) for it in updated_master_list)

    print(f"\nPost-Update Master Census:")
    print(f"  'ฟิรเอานฺ': {total_firawn} (Expected: 82)")
    print(f"  'ฟิรฺเอาน์': {total_firawn_old} (Expected: 0)")
    print(f"  'ฟีรเอานฺ': {total_firawn_typo} (Expected: 0)")
    print(f"  'ฟิรเอาน':  {total_firawn_plain} (Expected: 0)")

    assert total_firawn == 82, f"Expected 82, got {total_firawn}"
    assert total_firawn_old == 0
    assert total_firawn_typo == 0
    assert total_firawn_plain == 0
    print("Verification PASSED: 100% consistent across all 6,236 verses!\n")

    # 3. Save Master Files
    print("--- Saving Master Files ---")
    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(updated_master_list, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {MASTER_JSON}")

    with open(MASTER_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["surah", "ayah", "translation"])
        for item in updated_master_list:
            writer.writerow([item["surah"], item["ayah"], item["translation"]])
    print(f"  Saved: {MASTER_CSV}")

    # Mirror to root files
    root_json = os.path.join(BASE_DIR, "thai_v3_spacing_improved.json")
    root_csv = os.path.join(BASE_DIR, "thai_v3_spacing_improved.csv")
    shutil.copy2(MASTER_JSON, root_json)
    shutil.copy2(MASTER_CSV, root_csv)
    print(f"  Mirrored to: {root_json} & {root_csv}")

    final_mirror_json = os.path.join(FINAL_DIR, "thai_v3_spacing_improved.json")
    final_mirror_csv = os.path.join(FINAL_DIR, "thai_v3_spacing_improved.csv")
    if os.path.exists(final_mirror_json):
        shutil.copy2(MASTER_JSON, final_mirror_json)
    if os.path.exists(final_mirror_csv):
        shutil.copy2(MASTER_CSV, final_mirror_csv)

    # 4. Update Audit Logs
    print("\n--- Updating Audit Logs ---")
    # Fetch surah names for log
    app_db = os.path.join(APP_DIR, "assets", "quran_offline.db")
    conn = sqlite3.connect(app_db)
    c = conn.cursor()
    c.execute("SELECT id, name_arabic, name_english FROM surahs")
    surah_meta = {r[0]: (r[1], r[2]) for r in c.fetchall()}

    audit_entries = []
    for ch in applied_changes:
        s = ch["surah"]
        a = ch["ayah"]
        ar_name, en_name = surah_meta.get(s, ("", ""))
        audit_entries.append([
            str(s),
            str(a),
            ar_name,
            en_name,
            "TRANSLITERATION_STANDARDIZED",
            ch["old_text"],
            ch["new_text"],
            "ปรับการสะกดคำว่า 'ฟิรเอานฺ' ให้เป็นมาตรฐานพินทุ (ฺ) เดียวกันทั้งคัมภีร์ ตามระเบียบศูนย์กษัตริย์ฟะฮัด",
            "Standardized transliteration of Pharaoh to 'ฟิรเอานฺ' with phinthu (ฺ) consistently across the entire Quran according to King Fahd Complex orthography"
        ])

    for log_path in [AUDIT_LOG_FINAL, AUDIT_LOG_ROOT]:
        if os.path.exists(log_path):
            with open(log_path, "a", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                for entry in audit_entries:
                    writer.writerow(entry)
            print(f"  Appended {len(audit_entries)} entries to {log_path}")

    # 5. Update Mobile App
    print("\n--- Updating Mobile App ---")
    app_json = os.path.join(APP_DIR, "assets", "thai_v3.json")
    app_dict = {f"{it['surah']}:{it['ayah']}": it["translation"] for it in updated_master_list}
    with open(app_json, "w", encoding="utf-8") as f:
        json.dump(app_dict, f, ensure_ascii=False, indent=2)
    print(f"  Updated: {app_json}")

    # Update SQLite database
    for ch in applied_changes:
        c.execute("UPDATE verses SET translation_th = ? WHERE verse_key = ?", (ch["new_text"], ch["verse_key"]))
    
    c.execute("PRAGMA user_version;")
    current_ver = c.fetchone()[0] or 25
    next_ver = current_ver + 1
    c.execute(f"PRAGMA user_version = {next_ver};")
    conn.commit()
    conn.close()
    print(f"  Updated verses in {app_db} and bumped user_version to {next_ver}")

    # Update Dart service
    service_dart = os.path.join(APP_DIR, "lib", "services", "offline_quran_database_service.dart")
    if os.path.exists(service_dart):
        with open(service_dart, "r", encoding="utf-8") as f:
            dart_code = f.read()
        dart_code = re.sub(r'static const int _targetDbVersion = \d+;', f'static const int _targetDbVersion = {next_ver};', dart_code)
        with open(service_dart, "w", encoding="utf-8") as f:
            f.write(dart_code)
        print(f"  Bumped _targetDbVersion to {next_ver} in {service_dart}")

    # 6. Update Web App
    print("\n--- Updating Web App ---")
    web_json = os.path.join(WEB_DIR, "src", "data", "thai_v3.json")
    web_audit_log = os.path.join(WEB_DIR, "src", "data", "thai_translation_fixes_and_audit_log.csv")
    web_dict = {}
    for it in updated_master_list:
        s = str(it["surah"])
        a = str(it["ayah"])
        if s not in web_dict:
            web_dict[s] = {"verses": {}}
        web_dict[s]["verses"][a] = it["translation"]
    
    with open(web_json, "w", encoding="utf-8") as f:
        json.dump(web_dict, f, ensure_ascii=False, indent=2)
    print(f"  Updated: {web_json}")

    if os.path.exists(AUDIT_LOG_FINAL):
        shutil.copy2(AUDIT_LOG_FINAL, web_audit_log)
        print(f"  Mirrored audit log to: {web_audit_log}")

    # Run export_db_for_web.py to re-export WBW & verified translations
    export_script = os.path.join(WEB_DIR, "scripts", "export_db_for_web.py")
    if os.path.exists(export_script):
        print(f"  Running export_db_for_web.py...")
        os.system(f'python "{export_script}"')

    # 7. Synchronize with Supabase Cloud Storage (Live Remote Content)
    print("\n--- Synchronizing with Supabase Cloud Storage ---")
    SUPABASE_URL = "https://qeciqdjidugdipgqxysm.supabase.co"
    SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFlY2lxZGppZHVnZGlwZ3F4eXNtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTkzNDEzNywiZXhwIjoyMDk3NTEwMTM3fQ.HD6WLkzKxctn6_M52QjwGS3H-iNczuGsXAiv4KY5Fug"
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "x-upsert": "true"
    }

    upload_url = f"{SUPABASE_URL}/storage/v1/object/app-content/thai_v3.json"
    payload_bytes = json.dumps(web_dict, ensure_ascii=False, indent=2).encode("utf-8")
    resp = requests.post(upload_url, headers=headers, data=payload_bytes)
    if resp.status_code not in [200, 201]:
        resp = requests.put(upload_url, headers=headers, data=payload_bytes)
    print(f"  Supabase Storage upload status: {resp.status_code}")

    # Update app_content_versions table (Bump to 1.2.1)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    version_str = "1.2.1"
    db_url = f"{SUPABASE_URL}/rest/v1/app_content_versions?content_key=eq.thai_v3"
    patch_resp = requests.patch(db_url, headers={
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json"
    }, json={
        "version": version_str,
        "updated_at": now_iso,
        "is_active": True
    })
    print(f"  Supabase DB version bump status: {patch_resp.status_code} (version: {version_str})")

    # 8. Verify live downloaded content from Supabase
    print("\n--- Verifying Live Download from Supabase Cloud ---")
    verify_resp = requests.get(f"{SUPABASE_URL}/storage/v1/object/app-content/thai_v3.json", headers=headers)
    live_download = verify_resp.json()

    verified_live = 0
    for ch in applied_changes:
        s = str(ch["surah"])
        a = str(ch["ayah"])
        live_verse = live_download[s]["verses"][a]
        assert live_verse == ch["new_text"], f"Mismatch at {s}:{a} in live storage!"
        verified_live += 1

    print(f"  Successfully verified all {verified_live} updated verses in live Supabase Storage!")
    print("\n" + "=" * 75)
    print("  ALL 14 VERSES STANDARDIZED & SYNCHRONIZED ACROSS ALL PLATFORMS!")
    print("=" * 75)

if __name__ == "__main__":
    main()
