import json
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

app_path = "H:/gits/thai-quran-app/assets/thai_v3.json"
web_path = "H:/gits/thai-quran-web/src/data/thai_v3.json"
master_01_path = "final_files/01_thai_quran_translation_v3_master.json"

app_data = json.load(open(app_path, encoding="utf-8")) if os.path.exists(app_path) else {}
web_data = json.load(open(web_path, encoding="utf-8")) if os.path.exists(web_path) else {}
master_01 = json.load(open(master_01_path, encoding="utf-8")) if os.path.exists(master_01_path) else []

mismatches_app = 0
mismatches_web = 0

for item in master_01:
    key = f"{item['surah']}:{item['ayah']}"
    s, a = str(item['surah']), str(item['ayah'])

    t_master = item["translation"].strip()
    t_app = app_data.get(key, "").strip()
    t_web = web_data.get(s, {}).get("verses", {}).get(a, "").strip()

    if t_master != t_app:
        mismatches_app += 1
    if t_master != t_web:
        mismatches_web += 1

print(f"Mismatches between Master 01 and Live App: {mismatches_app} / 6236")
print(f"Mismatches between Master 01 and Live Web: {mismatches_web} / 6236")
