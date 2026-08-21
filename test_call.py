import os
import time
from google import genai
from google.genai import types

env_path = r"H:\gits\thai_quran_scholar_audit_v4\.env"
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        if "GEMINI_API_KEY_1" in line:
            k = line.split("=", 1)[1].strip().strip("'\"")

client = genai.Client(api_key=k)
t0 = time.time()
res = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents="Test prompt: return JSON []",
    config=types.GenerateContentConfig(response_mime_type="application/json")
)
print(f"Success in {time.time()-t0:.2f}s -> {res.text}")
