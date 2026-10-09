import urllib.request
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

pattern = re.compile(r'<sup\s+[^>]*foot_note="?(\d+)"?[^>]*>(.*?)</sup>', re.IGNORECASE)

for tid, name in [(203, "Hilali & Khan"), (149, "Bridges")]:
    url = f"https://api.quran.com/api/v4/quran/translations/{tid}?fields=verse_key"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    translations = data.get('translations', [])
    all_fn_ids = set()
    verses_with_fn = 0
    for t in translations:
        matches = pattern.findall(t.get('text', ''))
        if matches:
            verses_with_fn += 1
            for orig_id, num in matches:
                all_fn_ids.add(orig_id)
    print(f"{name} ({tid}): {len(translations)} verses, {verses_with_fn} verses with footnotes, {len(all_fn_ids)} unique footnote IDs")
