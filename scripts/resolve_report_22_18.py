#!/usr/bin/env python3
"""
Resolve Error Report for Surah 22 Ayah 18:
Fix missing space after 'เท่านั้น':
'แท้จริงอัลลอฮฺเท่านั้นผู้ที่อยู่ในชั้นฟ้าทั้งหลาย'
-> 'แท้จริงอัลลอฮฺเท่านั้น ผู้ที่อยู่ในชั้นฟ้าทั้งหลาย'
"""

import re
import os
import sqlite3
import shutil

TARGET_OLD = 'เท่านั้นผู้ที่'
TARGET_NEW = 'เท่านั้น ผู้ที่'

def replace_in_file(file_path):
    if not os.path.exists(file_path):
        print(f"Skipping non-existent: {file_path}")
        return 0
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    cnt = content.count(TARGET_OLD)
    if cnt > 0:
        content = content.replace(TARGET_OLD, TARGET_NEW)
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        print(f"Replaced {cnt} occurrence in {file_path}")
    else:
        print(f"No occurrences in {file_path}")
    return cnt

def update_sqlite_db(db_path, new_user_version):
    if not os.path.exists(db_path):
        print(f"Skipping non-existent DB: {db_path}")
        return
    print(f"\n--- Updating SQLite DB: {db_path} ---")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute(f"SELECT count(*) FROM verses WHERE surah_id = 22 AND verse_id = 18 AND translation_th LIKE '%{TARGET_OLD}%';")
    cnt = cur.fetchone()[0]
    if cnt > 0:
        cur.execute(f"UPDATE verses SET translation_th = REPLACE(translation_th, '{TARGET_OLD}', '{TARGET_NEW}') WHERE surah_id = 22 AND verse_id = 18;")
        print(f"  Updated row in verses.translation_th 22:18")
    else:
        print("  0 rows to update in verses.translation_th 22:18")
        
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
    print("RESOLVING SURAH 22 AYAH 18 SPACING REPORT")
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
        replace_in_file(path)
            
    # 2. thai-quran-web
    print("\n--- 2. thai-quran-web ---")
    web_files = [
        '/Users/admin/Documents/gits/thai-quran-web/src/data/thai_v3.json',
        '/Users/admin/Documents/gits/thai-quran-web/src/data/thai_footnotes.json',
    ]
    for path in web_files:
        replace_in_file(path)
            
    # 3. thai-quran-app
    print("\n--- 3. thai-quran-app ---")
    app_files = [
        '/Users/admin/Documents/gits/thai-quran-app/assets/thai_v3.json',
        '/Users/admin/Documents/gits/thai-quran-app/assets/footnotes/thai_footnotes.json',
    ]
    for path in app_files:
        replace_in_file(path)
    update_sqlite_db('/Users/admin/Documents/gits/thai-quran-app/assets/quran_offline.db', new_user_version=41)
    update_dart_version('/Users/admin/Documents/gits/thai-quran-app/lib/services/offline_quran_database_service.dart', 41)

    # 4. hifz-quran-app
    print("\n--- 4. hifz-quran-app ---")
    hifz_files = [
        '/Users/admin/Documents/gits/hifz-quran-app/assets/thai_v3.json',
        '/Users/admin/Documents/gits/hifz-quran-app/assets/footnotes/thai_footnotes.json',
        '/Users/admin/Documents/gits/hifz-quran-app/assets/merged_quran.json',
    ]
    for path in hifz_files:
        replace_in_file(path)
    update_sqlite_db('/Users/admin/Documents/gits/hifz-quran-app/assets/quran_offline.db', new_user_version=40)
    update_dart_version('/Users/admin/Documents/gits/hifz-quran-app/lib/services/offline_quran_database_service.dart', 40)

    # 5. wbw-translation-en-th
    print("\n--- 5. wbw-translation-en-th ---")
    wbw_files = [
        '/Users/admin/Documents/gits/wbw-translation-en-th/Quran-data/thai_v3.json',
        '/Users/admin/Documents/gits/wbw-translation-en-th/thai_footnotes.json',
    ]
    for path in wbw_files:
        replace_in_file(path)
    shutil.copyfile('/Users/admin/Documents/gits/thai-quran-web/src/data/thai_v3.json',
                    '/Users/admin/Documents/gits/wbw-translation-en-th/Quran-data/thai_v3.json')
    print("  Synced thai_v3.json to wbw-translation-en-th")

    print("\n==================================================")
    print("SURAH 22 AYAH 18 SPACING RESOLUTION COMPLETE!")
    print("==================================================")

if __name__ == '__main__':
    main()
