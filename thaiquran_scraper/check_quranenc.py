import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'https://quranenc.com/api/v1/translations/list'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        translations = data.get('translations', [])
        print(f"Total QuranEnc translations: {len(translations)}")
        for t in translations:
            lang = t.get('language_iso_code')
            if lang in ['en', 'ms', 'th', 'id']:
                print(f"{t.get('key')} | {lang} | {t.get('title')}")
except Exception as e:
    print('Error:', e)
