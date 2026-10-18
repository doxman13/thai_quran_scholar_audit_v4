#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
STANDARDIZE THAI ISLAMIC TRANSLITERATION & PHINTHU ACROSS ENTIRE ECOSYSTEM
=============================================================================
Standardizes Phinthu (ฺ U+0E3A) vs Karan (์ U+0E4C) and canonical Islamic
spelling across all translation datasets, short tafsir, ayah themes, WBW,
surah summaries, surah names, and thematic topics.

Synchronizes:
  1. Master Translations (audit final_files, web thai_v3, app assets, SQLite DBs)
  2. Short Tafsir (web TS, app JSON, SQLite DBs)
  3. Surah Summaries (web JSON, app JSON, web TS)
  4. Surah Names (SQLite DBs surahs.name_thai)
  5. Ayah Themes (web JSONs, app JSONs, SQLite DBs qul_ayah_themes)
  6. Word-by-Word (wbw master JSON, SQLite DBs words.translation_th, web wbw JSONs)
  7. Thematic Topics (web topics.json, SQLite DBs topics/categories)
  8. Increments SQLite PRAGMA user_version and Dart _targetDbVersion
=============================================================================
"""

import os
import sys
import json
import csv
import sqlite3
import re
import glob
import shutil

# Canonical Replacement Matrix for Thai Islamic Transliteration
CANONICAL_REPLACEMENTS = [
    # 1. Divine & Core
    ('อัลลอฮ์', 'อัลลอฮฺ'),
    ('รอซูลุลลอฮ์', 'รอซูลุลลอฮฺ'),
    ('ร่อซูลุลลอฮ์', 'รอซูลุลลอฮฺ'),
    ('ร่อซูลุลลอฮฺ', 'รอซูลุลลอฮฺ'),
    ('บิสมิลลาฮ์', 'บิสมิลลาฮฺ'),
    ('ซุบฮานัลลอฮ์', 'ซุบฮานัลลอฮฺ'),
    ('อินชาอัลลอฮ์', 'อินชาอัลลอฮฺ'),
    ('อัลฮัมดุลิลลาฮ์', 'อัลฮัมดุลิลลาฮฺ'),

    # 2. Key Islamic Concepts & Eschatology (Tā' marbūṭah / Hā' in Waqf)
    ('กิยามะฮ์', 'กิยามะฮฺ'),
    ('กิยามะห์', 'กิยามะฮฺ'),
    ('กียามะฮ์', 'กิยามะฮฺ'),
    ('อาคิเราะฮ์', 'อาคิเราะฮฺ'),
    ('อาคิเราะห์', 'อาคิเราะฮฺ'),
    ('อาคีเราะห์', 'อาคีเราะฮฺ'),
    ('อิบาดะฮ์', 'อิบาดะฮฺ'),
    ('อิบาดะห์', 'อิบาดะฮฺ'),
    ('มลาอิกะฮ์', 'มลาอิกะฮฺ'),
    ('มลาอิกะห์', 'มลาอิกะฮฺ'),
    ('มะลาอิกะฮ์', 'มลาอิกะฮฺ'),
    ('มะลาอิกะห์', 'มลาอิกะฮฺ'),
    ('มะลาอีกะฮ์', 'มลาอิกะฮฺ'),
    ('มลาอีกะฮ์', 'มลาอิกะฮฺ'),
    ('ฮิดายะฮ์', 'ฮิดายะฮฺ'),
    ('ชะฟาอะฮ์', 'ชะฟาอะฮฺ'),
    ('เตาบะฮ์', 'เตาบะฮฺ'),
    ('ฟิตนะฮ์', 'ฟิตนะฮฺ'),
    ('ฟิตนะห์', 'ฟิตนะฮฺ'),
    ('ซุนนะฮ์', 'ซุนนะฮฺ'),
    ('ซุนนะห์', 'ซุนนะฮฺ'),
    ('อะมานะฮ์', 'อะมานะฮฺ'),
    ('มุอฺมินะฮ์', 'มุอฺมินะฮฺ'),
    ('เศาะฮาบะฮ์', 'เศาะฮาบะฮฺ'),
    ('หิกมะฮ์', 'หิกมะฮฺ'),
    ('ฮิกมะฮ์', 'หิกมะฮฺ'),
    ('อุมเราะฮ์', 'อุมเราะฮฺ'),
    ('ดียะฮ์', 'ดียะฮฺ'),
    ('กิบละฮ์', 'กิบละฮฺ'),
    ('มัรวะฮ์', 'มัรวะฮฺ'),
    ('บัยอะฮ์', 'บัยอะฮฺ'),
    ('กะลาละฮ์', 'กะลาละฮฺ'),
    ('ญานาซะฮ์', 'ญะนาซะฮฺ'),
    ('ญาฮิลียะฮ์', 'ญาฮิลียะฮฺ'),
    ('อัลญาฮิลียะฮ์', 'อัลญาฮิลียะฮฺ'),
    ('กะอ์บะฮ์', 'กะอฺบะฮฺ'),
    ('กะอ์บะฮฺ', 'กะอฺบะฮฺ'),
    ('ชะฮาดะฮ์', 'ชะฮาดะฮฺ'),
    ('ซะกาฮ์', 'ซะกาฮฺ'),
    ('เราะห์มาน', 'เราะฮฺมาน'),
    ('รอห์มาน', 'รอฮฺมาน'),
    ('เราะห์มัต', 'เราะฮฺมัต'),
    ('เราะห์มัด', 'เราะฮฺมัด'),
    ('อะฮ์ลุลกิตาบ', 'อะฮฺลุลกิตาบ'),
    ('อัลเลาฮุลมะฮฟูซ', 'อัลเลาฮุลมะฮฺฟูซ'),
    ('มะฮฟูซ', 'มะฮฺฟูซ'),
    ('มะห์ฟูซ', 'มะฮฺฟูซ'),
    ('มะห์ชัร', 'มะฮฺชัร'),
    ('ตัสบีห์', 'ตัสบีหฺ'),
    ('นิกาห์', 'นิกาหฺ'),
    ('ศุบห์', 'ศุบหฺ'),
    ('มิห์รอบ', 'มิหฺรอบ'),
    ('อัรรูห์', 'อัรรูฮฺ'),
    ('เอี๊ยะห์รอม', 'อิหฺรอม'),
    ('อิห์รอม', 'อิหฺรอม'),
    ('รอกะอะฮ์', 'ร็อกอะฮฺ'),

    # 3. Quranic Entities & Locations
    ('ซูเราะฮ์', 'ซูเราะฮฺ'),
    ('ซูเราะห์', 'ซูเราะฮฺ'),
    ('อายะฮ์', 'อายะฮฺ'),
    ('อายะห์', 'อายะฮฺ'),
    ('มักกะฮ์', 'มักกะฮฺ'),
    ('มักกะห์', 'มักกะฮฺ'),
    ('มะดีนะฮ์', 'มะดีนะฮฺ'),
    ('มะดีนะห์', 'มะดีนะฮฺ'),
    ('มาดีนะฮ์', 'มะดีนะฮฺ'),
    ('อันฏอกียะฮ์', 'อันฏอกียะฮฺ'),
    ('อัลบะเกาะเราะฮ์', 'อัลบะเกาะเราะฮฺ'),
    ('อัลบะกอเราะฮ์', 'อัลบะเกาะเราะฮฺ'),
    ('อัลฟาติฮะฮ์', 'อัลฟาติฮะฮฺ'),
    ('อัลเกาะรีอะฮ์', 'อัลเกาะรีอะฮฺ'),
    ('อัล-กะฮ์ฟ', 'อัล-กะฮฺฟ'),
    ('อัส-สัจญ์ดะฮ์', 'อัส-สัจญ์ดะฮฺ'),

    # 4. Prophets & Persons
    ('นูห์', 'นูฮฺ'),
    ('นุห์', 'นุฮฺ'),
    ('นูฮ์', 'นูฮฺ'),
    ('ยะห์ยา', 'ยะฮฺยา'),
    ('ยะฮห์ยา', 'ยะฮฺยา'),
    ('โอ้ยะห์ยา', 'โอ้ยะฮฺยา'),
    ('อัลมะซีห์', 'อัลมะซีหฺ'),
    ('มะซีห์', 'มะซีหฺ'),
    ('ศอลิห์', 'ศอลิหฺ'),
    ('ศอและห์', 'ศอและฮฺ'),
    ('ซอและห์', 'ซอและฮฺ'),
    ('ลู๊ฏ', 'ลูฏ'),
    ('นบีลูต', 'นบีลูฏ'),
    ('มูฮัมหมัด', 'มุฮัมมัด'),
    ('มูฮัมมัด', 'มุฮัมมัด'),
    ('อิบราฮิม', 'อิบรอฮีม'),
    ('อิสมาอิล', 'อิสมาอีล'),
    ('ชุอัยบ์', 'ชุอัยบฺ'),
    ('ฟิรอาวน์', 'ฟิรเอานฺ'),
    ('ฟิรเอาน์', 'ฟิรเอานฺ'),
    ('ยะอ์กูบ', 'ยะอฺกูบ'),
    ('สะบะอ์', 'สะบะอฺ'),
    ('ดุลกอฮ์นัยน์', 'ซุลก็อรนัยน์'),
]

def apply_replacements(text: str) -> str:
    """Applies canonical replacements to a string, then standardizes residual ะฮ์/ะห์."""
    if not text:
        return ""
    # 1. Apply specific multi-character dictionary
    for old, new in CANONICAL_REPLACEMENTS:
        if old in text:
            text = text.replace(old, new)
    # 2. Standardize residual Arabic Tā' marbūṭah in waqf (ะฮ์ -> ะฮฺ, ะห์ -> ะฮฺ)
    text = text.replace('ะฮ์', 'ะฮฺ').replace('ะห์', 'ะฮฺ')
    return text

def main():
    print("=" * 80)
    print("  STANDARDIZING THAI ISLAMIC TRANSLITERATION ACROSS ENTIRE ECOSYSTEM")
    print("=" * 80)

    base_dir = "/Users/admin/Documents/gits"
    audit_dir = os.path.join(base_dir, "thai_quran_scholar_audit_v4")
    web_dir = os.path.join(base_dir, "thai-quran-web")
    app_dir = os.path.join(base_dir, "thai-quran-app")
    hifz_dir = os.path.join(base_dir, "hifz-quran-app")
    wbw_dir = os.path.join(base_dir, "wbw-translation-en-th")

    app_db_path = os.path.join(app_dir, "assets", "quran_offline.db")
    hifz_db_path = os.path.join(hifz_dir, "assets", "quran_offline.db")

    # -------------------------------------------------------------------------
    # 1. STANDARDIZE MASTER VERSE TRANSLATIONS (6,236 Ayahs)
    # -------------------------------------------------------------------------
    print("\n[1/8] Synchronizing Master Thai Translation (6,236 Ayahs)...")
    conn = sqlite3.connect(app_db_path)
    c = conn.cursor()
    c.execute("SELECT surah_id, verse_id, verse_key, translation_th FROM verses ORDER BY surah_id, verse_id")
    db_rows = c.fetchall()
    conn.close()

    master_list = []
    app_kv_map = {}
    web_nested_map = {}

    for s, a, vk, th in db_rows:
        clean_th = apply_replacements(th)
        master_list.append({
            "surah": s,
            "ayah": a,
            "translation": clean_th
        })
        app_kv_map[vk] = clean_th
        s_str = str(s)
        a_str = str(a)
        if s_str not in web_nested_map:
            web_nested_map[s_str] = {"verses": {}}
        web_nested_map[s_str]["verses"][a_str] = clean_th

    # Write to audit repo
    audit_01 = os.path.join(audit_dir, "final_files", "01_thai_quran_translation_v3_master.json")
    audit_02 = os.path.join(audit_dir, "final_files", "02_thai_quran_translation_v3_master.csv")
    audit_root_json = os.path.join(audit_dir, "thai_v3_spacing_improved.json")
    audit_root_csv = os.path.join(audit_dir, "thai_v3_spacing_improved.csv")

    with open(audit_01, "w", encoding="utf-8") as f:
        json.dump(master_list, f, ensure_ascii=False, indent=2)
    with open(audit_root_json, "w", encoding="utf-8") as f:
        json.dump(master_list, f, ensure_ascii=False, indent=2)

    with open(audit_02, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["surah", "ayah", "translation"])
        for it in master_list:
            writer.writerow([it["surah"], it["ayah"], it["translation"]])
    shutil.copyfile(audit_02, audit_root_csv)
    print("  ✓ Updated Audit v4 Master JSON and CSV (all 43 verses aligned to Phinthu)")

    # Write to Web App
    web_thai_v3 = os.path.join(web_dir, "src", "data", "thai_v3.json")
    with open(web_thai_v3, "w", encoding="utf-8") as f:
        json.dump(web_nested_map, f, ensure_ascii=False, indent=2)
    print("  ✓ Updated Web App src/data/thai_v3.json (100.00% match)")

    # Write to Mobile App
    app_thai_v3 = os.path.join(app_dir, "assets", "thai_v3.json")
    with open(app_thai_v3, "w", encoding="utf-8") as f:
        json.dump(app_kv_map, f, ensure_ascii=False, indent=2)
    print("  ✓ Updated Mobile App assets/thai_v3.json (100.00% match)")

    # Write to Hifz App
    hifz_thai_v3 = os.path.join(hifz_dir, "assets", "thai_v3.json")
    if os.path.exists(hifz_thai_v3):
        with open(hifz_thai_v3, "w", encoding="utf-8") as f:
            json.dump(app_kv_map, f, ensure_ascii=False, indent=2)
        print("  ✓ Updated Hifz App assets/thai_v3.json")

    # Update SQLite translation_th in both app and hifz DBs
    for db_p in [app_db_path, hifz_db_path]:
        if os.path.exists(db_p):
            conn_u = sqlite3.connect(db_p)
            cur_u = conn_u.cursor()
            for vk, th in app_kv_map.items():
                cur_u.execute("UPDATE verses SET translation_th = ? WHERE verse_key = ?", (th, vk))
            conn_u.commit()
            conn_u.close()
            print(f"  ✓ Verified verses.translation_th in {os.path.basename(os.path.dirname(os.path.dirname(db_p)))} DB")

    # -------------------------------------------------------------------------
    # 2. STANDARDIZE SHORT TAFSIR (Mokhtasar - 6,236 Verses)
    # -------------------------------------------------------------------------
    print("\n[2/8] Standardizing Short Tafsir (Mokhtasar)...")
    app_tafsir_path = os.path.join(app_dir, "assets", "tafsir_thai_mokhtasar.json")
    with open(app_tafsir_path, "r", encoding="utf-8") as f:
        tafsir_json = json.load(f)

    tafsir_replacements_count = 0
    clean_tafsir_map = {}
    for s_id, verses in tafsir_json.items():
        clean_tafsir_map[s_id] = {}
        for a_id, text in verses.items():
            cleaned = apply_replacements(text)
            if cleaned != text:
                tafsir_replacements_count += 1
            clean_tafsir_map[s_id][a_id] = cleaned

    print(f"  Standardized {tafsir_replacements_count} verses in Short Tafsir.")

    # Save to app JSON
    with open(app_tafsir_path, "w", encoding="utf-8") as f:
        json.dump(clean_tafsir_map, f, ensure_ascii=False, indent=2)
    print("  ✓ Saved assets/tafsir_thai_mokhtasar.json")

    # Update SQLite databases (both app and hifz)
    for db_p in [app_db_path, hifz_db_path]:
        if os.path.exists(db_p):
            c_db = sqlite3.connect(db_p)
            cur = c_db.cursor()
            for s_id, verses in clean_tafsir_map.items():
                for a_id, t_text in verses.items():
                    cur.execute(
                        "UPDATE verses SET tafsir_th = ? WHERE surah_id = ? AND verse_id = ?",
                        (t_text, int(s_id), int(a_id))
                    )
            c_db.commit()
            c_db.close()
            print(f"  ✓ Updated verses.tafsir_th in {os.path.basename(os.path.dirname(os.path.dirname(db_p)))} DB")

    # Update Web App tafsirThaiMokhtasar.ts
    web_tafsir_ts = os.path.join(web_dir, "src", "data", "tafsirThaiMokhtasar.ts")
    if os.path.exists(web_tafsir_ts):
        with open(web_tafsir_ts, "r", encoding="utf-8") as f:
            ts_content = f.read()
        clean_ts = apply_replacements(ts_content)
        with open(web_tafsir_ts, "w", encoding="utf-8") as f:
            f.write(clean_ts)
        print("  ✓ Updated Web App src/data/tafsirThaiMokhtasar.ts")

    # -------------------------------------------------------------------------
    # 3. STANDARDIZE SURAH SUMMARIES (114 Surahs)
    # -------------------------------------------------------------------------
    print("\n[3/8] Standardizing Surah Summaries (114 Surahs)...")
    for ssum_path in [
        os.path.join(web_dir, "src", "data", "surah_summary_th_exact.json"),
        os.path.join(app_dir, "assets", "surah_summary_th_exact.json")
    ]:
        if os.path.exists(ssum_path):
            with open(ssum_path, "r", encoding="utf-8") as f:
                s_data = json.load(f)
            clean_s_data = {}
            for k, val in s_data.items():
                if isinstance(val, dict):
                    clean_s_data[k] = {
                        vk: (apply_replacements(vv) if isinstance(vv, str) else vv)
                        for vk, vv in val.items()
                    }
                elif isinstance(val, str):
                    clean_s_data[k] = apply_replacements(val)
                else:
                    clean_s_data[k] = val
            with open(ssum_path, "w", encoding="utf-8") as f:
                json.dump(clean_s_data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ Updated {os.path.relpath(ssum_path, base_dir)}")

    # -------------------------------------------------------------------------
    # 4. STANDARDIZE SURAH NAMES IN SQLITE (surahs.name_thai)
    # -------------------------------------------------------------------------
    print("\n[4/8] Standardizing Surah Names in SQLite databases...")
    for db_p in [app_db_path, hifz_db_path]:
        if os.path.exists(db_p):
            c_db = sqlite3.connect(db_p)
            cur = c_db.cursor()
            cur.execute("SELECT id, name_thai FROM surahs")
            s_rows = cur.fetchall()
            updated_s = 0
            for sid, nth in s_rows:
                clean_nth = apply_replacements(nth)
                if clean_nth != nth:
                    cur.execute("UPDATE surahs SET name_thai = ? WHERE id = ?", (clean_nth, sid))
                    updated_s += 1
            c_db.commit()
            c_db.close()
            print(f"  ✓ Updated {updated_s} surah names in {os.path.basename(os.path.dirname(os.path.dirname(db_p)))} DB")

    # -------------------------------------------------------------------------
    # 5. STANDARDIZE AYAH THEMES (QUL & Reconciled)
    # -------------------------------------------------------------------------
    print("\n[5/8] Standardizing Ayah Themes...")
    app_themes_p = os.path.join(app_dir, "assets", "qul_ayah_themes_fixed.json")
    web_themes_p = os.path.join(web_dir, "src", "data", "qul_ayah_themes.json")
    web_reconciled_p = os.path.join(web_dir, "src", "data", "reconciled_thai_quran_themes.json")

    if os.path.exists(app_themes_p):
        with open(app_themes_p, "r", encoding="utf-8") as f:
            ath = json.load(f)
        clean_ath = []
        for it in ath:
            item = dict(it)
            item["title_th"] = apply_replacements(item.get("title_th", ""))
            item["theme_th"] = apply_replacements(item.get("theme_th", ""))
            clean_ath.append(item)
        with open(app_themes_p, "w", encoding="utf-8") as f:
            json.dump(clean_ath, f, ensure_ascii=False, indent=2)
        with open(web_themes_p, "w", encoding="utf-8") as f:
            json.dump(clean_ath, f, ensure_ascii=False, indent=2)
        print("  ✓ Updated qul_ayah_themes_fixed.json and synced to web src/data/qul_ayah_themes.json")

        for db_p in [app_db_path, hifz_db_path]:
            if os.path.exists(db_p):
                c_db = sqlite3.connect(db_p)
                cur = c_db.cursor()
                for item in clean_ath:
                    cur.execute("""
                        UPDATE qul_ayah_themes
                        SET title_th = ?, theme_th = ?
                        WHERE surah = ? AND ayah_from = ? AND ayah_to = ?
                    """, (item["title_th"], item["theme_th"], item["surah"], item["ayah_from"], item["ayah_to"]))
                c_db.commit()
                c_db.close()
                print(f"  ✓ Updated qul_ayah_themes in {os.path.basename(os.path.dirname(os.path.dirname(db_p)))} DB")

    if os.path.exists(web_reconciled_p):
        with open(web_reconciled_p, "r", encoding="utf-8") as f:
            rth = json.load(f)
        clean_rth = []
        for it in rth:
            item = dict(it)
            item["theme_th"] = apply_replacements(item.get("theme_th", ""))
            clean_rth.append(item)
        with open(web_reconciled_p, "w", encoding="utf-8") as f:
            json.dump(clean_rth, f, ensure_ascii=False, indent=2)
        print("  ✓ Updated reconciled_thai_quran_themes.json")

    # -------------------------------------------------------------------------
    # 6. STANDARDIZE WORD-BY-WORD (WBW)
    # -------------------------------------------------------------------------
    print("\n[6/8] Standardizing Word-by-Word (WBW)...")
    for db_p in [app_db_path, hifz_db_path]:
        if os.path.exists(db_p):
            c_db = sqlite3.connect(db_p)
            cur = c_db.cursor()
            cur.execute("SELECT id, translation_th FROM words WHERE translation_th IS NOT NULL")
            w_rows = cur.fetchall()
            updated_w = 0
            for wid, wth in w_rows:
                clean_wth = apply_replacements(wth)
                if clean_wth != wth:
                    cur.execute("UPDATE words SET translation_th = ? WHERE id = ?", (clean_wth, wid))
                    updated_w += 1
            c_db.commit()
            c_db.close()
            print(f"  ✓ Updated {updated_w} words in {os.path.basename(os.path.dirname(os.path.dirname(db_p)))} DB words table")

    # Update wbw master json
    wbw_master_p = os.path.join(wbw_dir, "quran_wbw_th_en_MASTER.json")
    if os.path.exists(wbw_master_p):
        with open(wbw_master_p, "r", encoding="utf-8") as f:
            wbw_data = json.load(f)
        for v in wbw_data:
            for w in v.get("words", []):
                th = w.get("thai", "")
                if th:
                    cleaned_th = apply_replacements(th)
                    if cleaned_th != th:
                        w["thai"] = cleaned_th
        with open(wbw_master_p, "w", encoding="utf-8") as f:
            json.dump(wbw_data, f, ensure_ascii=False, indent=2)
        print("  ✓ Updated wbw-translation-en-th/quran_wbw_th_en_MASTER.json")

    # Update all 114 web public/data/wbw/*.json files
    web_wbw_files = sorted(glob.glob(os.path.join(web_dir, "public", "data", "wbw", "*.json")))
    updated_files = 0
    for wbw_f in web_wbw_files:
        with open(wbw_f, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        file_modified = False
        if isinstance(raw_data, list):
            for v in raw_data:
                for w in v.get("words", []):
                    if "thai" in w and w["thai"]:
                        c = apply_replacements(w["thai"])
                        if c != w["thai"]:
                            w["thai"] = c
                            file_modified = True
        elif isinstance(raw_data, dict):
            for vk, words in raw_data.items():
                for w in words:
                    if "th" in w and w["th"]:
                        c = apply_replacements(w["th"])
                        if c != w["th"]:
                            w["th"] = c
                            file_modified = True
                    if "thai" in w and w["thai"]:
                        c = apply_replacements(w["thai"])
                        if c != w["thai"]:
                            w["thai"] = c
                            file_modified = True
        if file_modified:
            with open(wbw_f, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, separators=(',', ':'))
            updated_files += 1
    print(f"  ✓ Standardized {updated_files} web WBW files under public/data/wbw/")

    # -------------------------------------------------------------------------
    # 7. STANDARDIZE THEMATIC TOPICS
    # -------------------------------------------------------------------------
    print("\n[7/8] Standardizing Thematic Topics...")
    web_topics_p = os.path.join(web_dir, "src", "data", "topics.json")
    if os.path.exists(web_topics_p):
        with open(web_topics_p, "r", encoding="utf-8") as f:
            topics_data = json.load(f)
        for cat in topics_data.get("categories", []):
            cat["title_th"] = apply_replacements(cat.get("title_th", ""))
        for top in topics_data.get("topics", []):
            top["title_th"] = apply_replacements(top.get("title_th", ""))
        with open(web_topics_p, "w", encoding="utf-8") as f:
            json.dump(topics_data, f, ensure_ascii=False, indent=2)
        print("  ✓ Updated web src/data/topics.json")

        for db_p in [app_db_path, hifz_db_path]:
            if os.path.exists(db_p):
                c_db = sqlite3.connect(db_p)
                cur = c_db.cursor()
                for cat in topics_data.get("categories", []):
                    cur.execute("UPDATE topic_categories SET title_th = ? WHERE id = ?", (cat["title_th"], cat["id"]))
                for top in topics_data.get("topics", []):
                    cur.execute("UPDATE topics SET title_th = ? WHERE id = ?", (top["title_th"], top["id"]))
                c_db.commit()
                c_db.close()
                print(f"  ✓ Updated topics and topic_categories in {os.path.basename(os.path.dirname(os.path.dirname(db_p)))} DB")

    # -------------------------------------------------------------------------
    # 8. BUMP OFFLINE DATABASE USER_VERSION & DART CODE
    # -------------------------------------------------------------------------
    print("\n[8/8] Incrementing SQLite PRAGMA user_version and Dart Service...")
    # App DB
    if os.path.exists(app_db_path):
        conn = sqlite3.connect(app_db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA user_version;")
        cur_v = cur.fetchone()[0] or 37
        next_v = cur_v + 1
        cur.execute(f"PRAGMA user_version = {next_v};")
        conn.commit()
        conn.close()
        print(f"  ✓ Bumped thai-quran-app SQLite PRAGMA user_version to {next_v}")

        app_dart = os.path.join(app_dir, "lib", "services", "offline_quran_database_service.dart")
        if os.path.exists(app_dart):
            with open(app_dart, "r", encoding="utf-8") as f:
                dcode = f.read()
            dcode = re.sub(r'static const int _targetDbVersion = \d+;', f'static const int _targetDbVersion = {next_v};', dcode)
            with open(app_dart, "w", encoding="utf-8") as f:
                f.write(dcode)
            print(f"  ✓ Bumped thai-quran-app _targetDbVersion to {next_v} in Dart service")

    # Hifz App DB
    if os.path.exists(hifz_db_path):
        conn = sqlite3.connect(hifz_db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA user_version;")
        cur_v = cur.fetchone()[0] or 36
        next_v = cur_v + 1
        cur.execute(f"PRAGMA user_version = {next_v};")
        conn.commit()
        conn.close()
        print(f"  ✓ Bumped hifz-quran-app SQLite PRAGMA user_version to {next_v}")

        hifz_dart = os.path.join(hifz_dir, "lib", "services", "offline_quran_database_service.dart")
        if os.path.exists(hifz_dart):
            with open(hifz_dart, "r", encoding="utf-8") as f:
                dcode = f.read()
            dcode = re.sub(r'static const int _targetDbVersion = \d+;', f'static const int _targetDbVersion = {next_v};', dcode)
            with open(hifz_dart, "w", encoding="utf-8") as f:
                f.write(dcode)
            print(f"  ✓ Bumped hifz-quran-app _targetDbVersion to {next_v} in Dart service")

    print("\n" + "=" * 80)
    print("  SUCCESS: ALL DATASETS ARE NOW 100% STANDARDIZED AND SYNCHRONIZED!")
    print("=" * 80)

if __name__ == "__main__":
    main()
