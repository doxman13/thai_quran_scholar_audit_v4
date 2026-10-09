import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

print("1. Fetching all Saheeh International translations...")
url = "https://api.quran.com/api/v4/quran/translations/20?fields=verse_key"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

translations = data.get('translations', [])
print(f"   Fetched {len(translations)} verses.")

pattern = re.compile(r'<sup foot_note=(\d+)>(\d+)</sup>')

verse_data = {}
all_fn_ids = set()

for t in translations:
    vkey = t.get('verse_key')
    raw_text = t.get('text', '')
    
    matches = pattern.findall(raw_text)
    if not matches:
        continue

    # matches is list of (orig_fn_id, relative_num)
    # Convert <sup foot_note=X>Y</sup> to [Y]
    annotated = pattern.sub(r'[\2]', raw_text)
    
    fn_list = []
    for orig_id_str, rel_num_str in matches:
        orig_id = int(orig_id_str)
        rel_num = int(rel_num_str)
        all_fn_ids.add(orig_id)
        fn_list.append({
            'id': rel_num,
            'origId': orig_id,
            'text': ''
        })
    
    verse_data[vkey] = {
        'annotated': annotated,
        'footnotes': fn_list
    }

print(f"2. Found {len(verse_data)} verses with footnotes.")
print(f"   Found {len(all_fn_ids)} unique footnote IDs to fetch.")

fn_text_cache = {}

def fetch_single_footnote(fid):
    fn_url = f"https://api.quran.com/api/v4/foot_notes/{fid}"
    fn_req = urllib.request.Request(fn_url, headers={'User-Agent': 'Mozilla/5.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(fn_req, timeout=10) as fn_resp:
                fn_json = json.loads(fn_resp.read().decode('utf-8'))
                text = fn_json.get('foot_note', {}).get('text', '').strip()
                return fid, text
        except Exception as e:
            time.sleep(0.5)
    return fid, ''

print("3. Fetching footnote texts in parallel (max_workers=25)...")
start_time = time.time()
completed = 0
total = len(all_fn_ids)

with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
    future_to_fid = {executor.submit(fetch_single_footnote, fid): fid for fid in all_fn_ids}
    for future in concurrent.futures.as_completed(future_to_fid):
        fid, text = future.result()
        fn_text_cache[fid] = text
        completed += 1
        if completed % 200 == 0 or completed == total:
            elapsed = time.time() - start_time
            rate = completed / elapsed if elapsed > 0 else 0
            print(f"   Progress: {completed}/{total} ({completed*100//total}%) [{rate:.1f} notes/sec]")

print("4. Assembling final dataset...")
missing_count = 0
for vkey, vinfo in verse_data.items():
    for fn in vinfo['footnotes']:
        text = fn_text_cache.get(fn['origId'], '')
        if not text:
            missing_count += 1
        fn['text'] = text

print(f"   Done. Missing texts: {missing_count}")

# Save to destination directories
destinations = [
    "H:/gits/thai_quran_scholar_audit_v4/thaiquran_scraper/en_saheeh_footnotes.json",
    "H:/gits/thai-quran-web/src/data/en_saheeh_footnotes.json",
    "H:/gits/thai-quran-app/assets/footnotes/en_saheeh_footnotes.json",
]

for dest in destinations:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', encoding='utf-8') as f:
        json.dump(verse_data, f, ensure_ascii=False, indent=None)
    print(f"   Saved to {dest} ({os.path.getsize(dest)} bytes)")

print("✅ Saheeh International footnotes successfully generated!")
