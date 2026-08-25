import requests
import json
import os
import sys
import datetime

sys.stdout.reconfigure(encoding='utf-8')

SUPABASE_URL = "https://qeciqdjidugdipgqxysm.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFlY2lxZGppZHVnZGlwZ3F4eXNtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTkzNDEzNywiZXhwIjoyMDk3NTEwMTM3fQ.HD6WLkzKxctn6_M52QjwGS3H-iNczuGsXAiv4KY5Fug"

headers = {
    "apikey": SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
}

# 1. Load Master Data from Final Files
master_json_path = r"H:\gits\thai_quran_scholar_audit_v4\final_files\01_thai_quran_translation_v3_master.json"
with open(master_json_path, "r", encoding="utf-8") as f:
    master_list = json.load(f)

print(f"Loaded master translation dataset: {len(master_list)} verses.")

# Format as nested dictionary for Web & Mobile remote content service
nested_dict = {}
for it in master_list:
    s = str(it["surah"])
    a = str(it["ayah"])
    if s not in nested_dict:
        nested_dict[s] = {"verses": {}}
    nested_dict[s]["verses"][a] = it["translation"]

# Convert to JSON string bytes
json_bytes = json.dumps(nested_dict, ensure_ascii=False, indent=2).encode("utf-8")
print(f"Payload size: {len(json_bytes)} bytes ({len(json_bytes)/1024/1024:.2f} MB)")

# 2. Upload to Supabase Storage app-content/thai_v3.json
print("\n--- Uploading thai_v3.json to Supabase Storage (app-content/thai_v3.json) ---")
upload_url = f"{SUPABASE_URL}/storage/v1/object/app-content/thai_v3.json"
upload_headers = {
    **headers,
    "Content-Type": "application/json",
    "x-upsert": "true"
}

resp = requests.post(upload_url, headers=upload_headers, data=json_bytes)
print("POST status:", resp.status_code, resp.text)

if resp.status_code not in [200, 201]:
    resp = requests.put(upload_url, headers=upload_headers, data=json_bytes)
    print("PUT status:", resp.status_code, resp.text)

# 3. Update app_content_versions table (Bump to v1.2.0)
now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(f"\n--- Updating app_content_versions table (version: 1.2.0, timestamp: {now_iso}) ---")
update_url = f"{SUPABASE_URL}/rest/v1/app_content_versions?content_key=eq.thai_v3"
update_payload = {
    "version": "1.2.0",
    "updated_at": now_iso,
    "is_active": True
}
update_headers = {
    **headers,
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}
resp_db = requests.patch(update_url, headers=update_headers, json=update_payload)
print("DB version update status:", resp_db.status_code, resp_db.text)

# 4. Download and verify live content from Supabase
print("\n--- Verifying live content from Supabase Storage ---")
verify_resp = requests.get(f"{SUPABASE_URL}/storage/v1/object/app-content/thai_v3.json", headers=headers)
downloaded_json = verify_resp.json()

downloaded_dict = {}
for s, s_obj in downloaded_json.items():
    for a, t in s_obj.get("verses", {}).items():
        downloaded_dict[f"{s}:{a}"] = t

master_dict = {f"{x['surah']}:{x['ayah']}": x['translation'] for x in master_list}

diffs = []
for k, master_val in master_dict.items():
    dl_val = downloaded_dict.get(k)
    if dl_val != master_val:
        diffs.append((k, master_val, dl_val))

print(f"Downloaded verses count: {len(downloaded_dict)}")
print(f"Verse 11:35 in Supabase: {downloaded_dict.get('11:35')}")
print(f"Differences against Master: {len(diffs)}")

if len(diffs) == 0 and len(downloaded_dict) == 6236:
    print("\n>>> SUCCESS: Supabase is 100% in sync with the Master Translation Dataset! <<<")
else:
    print("\n>>> WARNING: Mismatches found! <<<")
