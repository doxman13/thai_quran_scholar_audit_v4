import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

SUP_PATTERN = re.compile(r'<sup\s+[^>]*foot_note="?(\d+)"?[^>]*>(.*?)</sup>', re.IGNORECASE)
TAG_CLEANER = re.compile(r'</?(?:span|i|b|em|strong|u|p|div|a)[^>]*>', re.IGNORECASE)

def clean_html_tags(text: str) -> str:
    # Clean basic formatting tags while preserving footnote sups
    cleaned = TAG_CLEANER.sub('', text)
    # Clean up any leftover duplicate spaces
    cleaned = re.sub(r'[ \t]+', ' ', cleaned).strip()
    return cleaned

def process_translation(tid: int, key_name: str, display_name: str):
    print(f"\n=======================================================")
    print(f"Processing {display_name} (Resource ID: {tid})...")
    print(f"=======================================================")
    
    url = f"https://api.quran.com/api/v4/quran/translations/{tid}?fields=verse_key"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    
    raw_translations = data.get('translations', [])
    print(f"1. Fetched {len(raw_translations)} verses.")
    
    plain_text_map = {}
    verse_footnotes_map = {}
    unique_fn_ids = set()
    
    for item in raw_translations:
        vkey = item.get('verse_key')
        raw_text = item.get('text', '')
        
        # Clean plain text without footnotes
        plain_text = SUP_PATTERN.sub('', raw_text)
        plain_text = clean_html_tags(plain_text)
        plain_text_map[vkey] = plain_text
        
        matches = SUP_PATTERN.findall(raw_text)
        if not matches:
            continue
        
        # Create annotated text with [1], [2]
        # First clean non-footnote tags
        working_annotated = clean_html_tags(raw_text)
        # Then replace <sup ...>X</sup> with [X]
        annotated = SUP_PATTERN.sub(r'[\2]', working_annotated)
        
        fn_list = []
        for orig_id_str, rel_num_str in matches:
            orig_id = int(orig_id_str)
            rel_num = int(rel_num_str) if rel_num_str.isdigit() else (len(fn_list) + 1)
            unique_fn_ids.add(orig_id)
            fn_list.append({
                'id': rel_num,
                'origId': orig_id,
                'text': ''
            })
        
        verse_footnotes_map[vkey] = {
            'annotated': annotated,
            'footnotes': fn_list
        }
    
    print(f"2. Found {len(verse_footnotes_map)} verses with footnotes.")
    print(f"   Found {len(unique_fn_ids)} unique footnote IDs to fetch.")
    
    fn_text_cache = {}
    
    def fetch_fn(fid):
        fn_url = f"https://api.quran.com/api/v4/foot_notes/{fid}"
        fn_req = urllib.request.Request(fn_url, headers={'User-Agent': 'Mozilla/5.0'})
        for _ in range(3):
            try:
                with urllib.request.urlopen(fn_req, timeout=10) as fn_resp:
                    fn_json = json.loads(fn_resp.read().decode('utf-8'))
                    raw_fn_text = fn_json.get('foot_note', {}).get('text', '').strip()
                    # Clean any tags in footnote text
                    clean_fn = clean_html_tags(raw_fn_text)
                    return fid, clean_fn
            except Exception:
                time.sleep(0.4)
        return fid, ''
    
    print(f"3. Fetching footnote texts with 30 workers...")
    start_time = time.time()
    completed = 0
    total = len(unique_fn_ids)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_fid = {executor.submit(fetch_fn, fid): fid for fid in unique_fn_ids}
        for future in concurrent.futures.as_completed(future_to_fid):
            fid, text = future.result()
            fn_text_cache[fid] = text
            completed += 1
            if completed % 250 == 0 or completed == total:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                print(f"   Progress: {completed}/{total} ({completed*100//total}%) [{rate:.1f} notes/sec]")
    
    # Fill in texts
    missing_count = 0
    for vkey, vinfo in verse_footnotes_map.items():
        for fn in vinfo['footnotes']:
            text = fn_text_cache.get(fn['origId'], '')
            if not text:
                missing_count += 1
            fn['text'] = text
    
    print(f"4. Assembly complete. Missing texts: {missing_count}")
    
    # Save files
    targets = [
        # Plain text
        (f"H:/gits/thai-quran-web/src/data/{key_name}.json", plain_text_map),
        (f"H:/gits/thai-quran-app/assets/{key_name}.json", plain_text_map),
        # Footnotes
        (f"H:/gits/thai-quran-web/src/data/{key_name}_footnotes.json", verse_footnotes_map),
        (f"H:/gits/thai-quran-app/assets/footnotes/{key_name}_footnotes.json", verse_footnotes_map),
        (f"H:/gits/thai_quran_scholar_audit_v4/thaiquran_scraper/{key_name}_footnotes.json", verse_footnotes_map),
    ]
    
    for filepath, content in targets:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=None)
        print(f"   Saved {filepath} ({os.path.getsize(filepath)} bytes)")
    
    print(f"✅ {display_name} successfully processed!")

if __name__ == '__main__':
    # 1. Al-Hilali & Muhsin Khan (Resource 203)
    process_translation(203, "en_hilali_khan", "Al-Hilali & Muhsin Khan")
    # 2. Bridges' Translation (Resource 149)
    process_translation(149, "en_bridges", "Bridges' Translation (Fadel Soliman)")
