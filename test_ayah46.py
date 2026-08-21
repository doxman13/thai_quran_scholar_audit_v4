import os
import sys
import json
import time
from google import genai
from google.genai import types

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

env_path = r"H:\gits\thai_quran_scholar_audit_v4\.env"
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        if "GEMINI_API_KEY_1" in line:
            k1 = line.split("=", 1)[1].strip().strip("'\"")

master_file = r"H:\gits\thai_quran_scholar_audit_v4\step2_tri_lingual_master.json"
with open(master_file, "r", encoding="utf-8") as f:
    master = json.load(f)

v46 = [v for v in master if v["surah"] == 12 and v["ayah"] == 46][0]
print("Testing Surah 12 Ayah 46 with Key 1:")

prompt = f"""--- AYAH 46 ---
[Arabic Uthmani]: {v46['arabic']}
[Malay Basmeih ]: {v46['malay']}
[Thai v3 Master]: {v46['thai']}

Audit for typos or mistranslations. Output JSON array."""

client = genai.Client(api_key=k1)
t0 = time.time()
try:
    res = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    print(f"Done in {time.time()-t0:.2f}s: {res.text}")
except Exception as e:
    print(f"Error in {time.time()-t0:.2f}s: {e}")
