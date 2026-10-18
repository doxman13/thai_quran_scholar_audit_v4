#!/usr/bin/env python3
"""
Standardize 'นะบี' -> 'นบี' across the Thai Quran ecosystem:
- Master translation files (JSON, CSV)
- Web application (translations, tafsir, footnotes, themes, root forms)
- Mobile apps (thai-quran-app & hifz-quran-app: JSON, SQLite DB, version bump)
- WBW translation repository (data, footnotes, gloss maps)
"""

import re
import os
import sqlite3

def replace_in_file(file_path, old_str, new_str):
    if not os.path.exists(file_path):
        print(f"Skipping non-existent: {file_path}")
        return 0
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    count = len(re.findall(old_str, content))
    if count > 0:
        new_content = content.replace(old_str, new_str)
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.write(new_content)
        print(f"Replaced {count:2d} occurrences in {file_path}")
    else:
        print(f"No occurrences of '{old_str}' in {file_path}")
    return count

def update_sqlite_db(db_path, new_user_version):
    if not os.path.exists(db_path):
        print(f"Skipping non-existent DB: {db_path}")
        return
    print(f"\n--- Updating SQLite DB: {db_path} ---")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. verses.translation_th
    cur.execute("SELECT count(*) FROM verses WHERE translation_th LIKE '%นะบี%';")
    v_cnt = cur.fetchone()[0]
    if v_cnt > 0:
        cur.execute("UPDATE verses SET translation_th = REPLACE(translation_th, 'นะบี', 'นบี') WHERE translation_th LIKE '%นะบี%';")
        print(f"  Updated {cur.rowcount} rows in verses.translation_th")
    else:
        print("  0 rows to update in verses.translation_th")
        
    # 2. verses.tafsir_th
    cur.execute("SELECT count(*) FROM verses WHERE tafsir_th LIKE '%นะบี%';")
    t_cnt = cur.fetchone()[0]
    if t_cnt > 0:
        cur.execute("UPDATE verses SET tafsir_th = REPLACE(tafsir_th, 'นะบี', 'นบี') WHERE tafsir_th LIKE '%นะบี%';")
        print(f"  Updated {cur.rowcount} rows in verses.tafsir_th")
    else:
        print("  0 rows to update in verses.tafsir_th")
        
    # 3. Check any other columns
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall() if not r[0].startswith('sqlite_')]
    for t in tables:
        if t == 'verses': continue
        cur.execute(f"PRAGMA table_info({t});")
        cols = [c[1] for c in cur.fetchall() if c[2].upper() in ('TEXT', 'VARCHAR', 'CHAR', '')]
        for col in cols:
            try:
                cur.execute(f"SELECT count(*) FROM \"{t}\" WHERE \"{col}\" LIKE '%นะบี%';")
                cnt = cur.fetchone()[0]
                if cnt > 0:
                    cur.execute(f"UPDATE \"{t}\" SET \"{col}\" = REPLACE(\"{col}\", 'นะบี', 'นบี') WHERE \"{col}\" LIKE '%นะบี%';")
                    print(f"  Updated {cur.rowcount} rows in {t}.{col}")
            except Exception:
                pass
                
    # 4. Bump user_version
    cur.execute("PRAGMA user_version;")
    old_ver = cur.fetchone()[0]
    cur.execute(f"PRAGMA user_version = {new_user_version};")
    conn.commit()
    conn.close()
    print(f"  Bumped user_version from {old_ver} to {new_user_version}")

def update_dart_version(file_path, new_version):
    if not os.path.exists(file_path):
        print(f"Skipping non-existent: {file_path}")
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = re.sub(
        r'static const int _targetDbVersion = \d+;',
        f'static const int _targetDbVersion = {new_version};',
        content
    )
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Updated _targetDbVersion to {new_version} in {file_path}")

def main():
    print("==================================================")
    print("STANDARDIZING 'นะบี' -> 'นบี' ACROSS ENTIRE ECOSYSTEM")
    print("==================================================")
    
    # 1. thai_quran_scholar_audit_v4
    print("\n--- 1. thai_quran_scholar_audit_v4 ---")
    audit_files = [
        '/Users/admin/Documents/gits/thai_quran_scholar_audit_v4/final_files/01_thai_quran_translation_v3_master.json',
        '/Users/admin/Documents/gits/thai_quran_scholar_audit_v4/final_files/02_thai_quran_translation_v3_master.csv',
        '/Users/admin/Documents/gits/thai_quran_scholar_audit_v4/final_files/08_tri_lingual_master_arabic_malay_thai.json',
        '/Users/admin/Documents/gits/thai_quran_scholar_audit_v4/final_files/09_quran_foundation_api_resource_id230.json',
        '/Users/admin/Documents/gits/thai_quran_scholar_audit_v4/final_files/thai_v3_spacing_improved.json',
        '/Users/admin/Documents/gits/thai_quran_scholar_audit_v4/final_files/thai_v3_spacing_improved.csv',
        '/Users/admin/Documents/gits/thai_quran_scholar_audit_v4/step2_tri_lingual_master.json',
        '/Users/admin/Documents/gits/thai_quran_scholar_audit_v4/quran_foundation_thai_id230.json',
    ]
    for path in audit_files:
        replace_in_file(path, 'นะบี', 'นบี')
            
    # 2. thai-quran-web
    print("\n--- 2. thai-quran-web ---")
    web_files = [
        '/Users/admin/Documents/gits/thai-quran-web/src/data/thai_v3.json',
        '/Users/admin/Documents/gits/thai-quran-web/src/data/tafsirThaiMokhtasar.ts',
        '/Users/admin/Documents/gits/thai-quran-web/src/data/thai_footnotes.json',
        '/Users/admin/Documents/gits/thai-quran-web/src/data/reconciled_thai_quran_themes.json',
        '/Users/admin/Documents/gits/thai-quran-web/public/data/root_forms.json',
    ]
    for path in web_files:
        replace_in_file(path, 'นะบี', 'นบี')
            
    # 3. thai-quran-app
    print("\n--- 3. thai-quran-app ---")
    app_files = [
        '/Users/admin/Documents/gits/thai-quran-app/assets/thai_v3.json',
        '/Users/admin/Documents/gits/thai-quran-app/assets/tafsir_thai_mokhtasar.json',
        '/Users/admin/Documents/gits/thai-quran-app/assets/footnotes/thai_footnotes.json',
        '/Users/admin/Documents/gits/thai-quran-app/assets/wbw_thai_gloss_map.json',
    ]
    for path in app_files:
        replace_in_file(path, 'นะบี', 'นบี')
    update_sqlite_db('/Users/admin/Documents/gits/thai-quran-app/assets/quran_offline.db', new_user_version=39)
    update_dart_version('/Users/admin/Documents/gits/thai-quran-app/lib/services/offline_quran_database_service.dart', 39)

    # 4. hifz-quran-app
    print("\n--- 4. hifz-quran-app ---")
    hifz_themes = '/Users/admin/Documents/gits/hifz-quran-app/assets/reconciled_thai_quran_themes.json'
    replace_in_file(hifz_themes, 'นะบีชุอัยบ์', 'นบีชุอัยบฺ')
    replace_in_file(hifz_themes, 'นะบี', 'นบี')

    hifz_files = [
        '/Users/admin/Documents/gits/hifz-quran-app/assets/thai_v3.json',
        '/Users/admin/Documents/gits/hifz-quran-app/assets/tafsir_thai_mokhtasar.json',
        '/Users/admin/Documents/gits/hifz-quran-app/assets/footnotes/thai_footnotes.json',
        '/Users/admin/Documents/gits/hifz-quran-app/assets/merged_quran.json',
    ]
    for path in hifz_files:
        replace_in_file(path, 'นะบี', 'นบี')
    update_sqlite_db('/Users/admin/Documents/gits/hifz-quran-app/assets/quran_offline.db', new_user_version=38)
    update_dart_version('/Users/admin/Documents/gits/hifz-quran-app/lib/services/offline_quran_database_service.dart', 38)

    # 5. wbw-translation-en-th
    print("\n--- 5. wbw-translation-en-th ---")
    wbw_files = [
        '/Users/admin/Documents/gits/wbw-translation-en-th/Quran-data/thai_v3.json',
        '/Users/admin/Documents/gits/wbw-translation-en-th/thai_footnotes.json',
        '/Users/admin/Documents/gits/wbw-translation-en-th/wbw_thai_gloss_map.json',
        '/Users/admin/Documents/gits/wbw-translation-en-th/wbw_thai_gloss_map_fixed.json',
    ]
    for path in wbw_files:
        replace_in_file(path, 'นะบี', 'นบี')

    print("\n==================================================")
    print("STANDARDIZATION COMPLETE!")
    print("==================================================")

if __name__ == '__main__':
    main()
