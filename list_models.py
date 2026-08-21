import os
from google import genai

env_path = r"H:\gits\thai_quran_scholar_audit_v4\.env"
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        if "GEMINI_API_KEY_3" in line:
            k = line.split("=", 1)[1].strip().strip("'\"")

client = genai.Client(api_key=k)
models = client.models.list()
for m in models:
    if "flash" in m.name.lower() or "lite" in m.name.lower():
        print(m.name)
