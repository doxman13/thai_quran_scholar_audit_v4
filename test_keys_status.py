import os
from google import genai

env_path = r"H:\gits\thai_quran_scholar_audit_v4\.env"
keys = []
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("#") or not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip("'\"")
        if "GEMINI_API_KEY" in k and v:
            keys.append((k, v))

for name, k in keys:
    client = genai.Client(api_key=k)
    try:
        res = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents="Say 'OK'"
        )
        print(f"Key {name}: SUCCESS -> {res.text.strip()}")
    except Exception as e:
        print(f"Key {name}: ERROR -> {e}")
