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

models_to_test = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash"]

for name, k in keys:
    client = genai.Client(api_key=k)
    print(f"\nTesting {name}:")
    for m in models_to_test:
        try:
            res = client.models.generate_content(
                model=m,
                contents="Reply only with the word OK"
            )
            print(f"  [{m}]: SUCCESS -> {res.text.strip()}")
        except Exception as e:
            err = str(e)
            if "429" in err:
                print(f"  [{m}]: 429 Quota Exceeded")
            else:
                print(f"  [{m}]: ERROR -> {err[:60]}")
