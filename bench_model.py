import time
import os
from google import genai
from google.genai import types

env_path = r"H:\gits\thai_quran_scholar_audit_v4\.env"
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        if "GEMINI_API_KEY_1" in line:
            k1 = line.split("=", 1)[1].strip().strip("'\"")
        if "GEMINI_API_KEY_3" in line:
            k3 = line.split("=", 1)[1].strip().strip("'\"")

for m in ["gemini-3.5-flash-lite", "gemini-2.5-flash"]:
    client = genai.Client(api_key=k1)
    t0 = time.time()
    try:
        res = client.models.generate_content(
            model=m,
            contents="Audit this Thai translation: 'พระองค์ผู้ทรงกรุณาปรานี ผู้ทรงเมตตาเสมอ'. Is there any typo? Reply JSON []",
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        print(f"Model {m} on Key 1: {time.time()-t0:.2f}s -> {res.text.strip()}")
    except Exception as e:
        print(f"Model {m} on Key 1: {time.time()-t0:.2f}s -> ERROR: {e}")
