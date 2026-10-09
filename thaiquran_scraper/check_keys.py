import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

# 1. Fetch all 6,236 verses of Saheeh International (Resource 20)
print("Fetching all Saheeh International verses from Quran.com...")
url = "https://api.quran.com/api/v4/quran/translations/20"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

raw_translations = data.get('translations', [])
print(f"Total verses fetched: {len(raw_translations)}")

# Map of verse_key -> { 'annotated': str, 'footnotes': [ {'id': int, 'origId': int, 'text': ''} ] }
verse_footnotes = {}
all_footnote_ids = set()
pattern = re.compile(r'<sup foot_note=(\d+)>(\d+)</sup>')

for item in raw_translations:
    raw_text = item.get('text', '')
    # Check if there are any footnotes
    matches = pattern.findall(raw_text)
    if not matches:
        continue
    
    # Extract surah and ayah number from verse_id or resource_id
    # Wait, raw_translations has resource_id, text. Does it have verse_key?
    # Let's check keys in an item:
    verse_key = item.get('verse_key')
    if not verse_key:
        # If verse_key is missing, derive it from loop index or verse_id
        # Let's check item keys!
        pass

print("Sample item keys:", raw_translations[0].keys())
