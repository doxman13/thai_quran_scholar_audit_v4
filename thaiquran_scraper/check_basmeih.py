import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("1. Checking Tanzil.net ms.basmeih...")
tanzil_url = "http://tanzil.net/trans/ms.basmeih"
req = urllib.request.Request(tanzil_url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode('utf-8')
        lines = [line for line in content.splitlines() if line and not line.startswith('#')]
        print(f"   Tanzil lines: {len(lines)}")
        sample = lines[:10]
        has_brackets = sum(1 for line in lines if re.search(r'\[\d+\]', line))
        has_footnotes = sum(1 for line in lines if 'nota' in line.lower() or 'rujuk' in line.lower())
        print(f"   Sample: {sample[1] if len(sample) > 1 else ''}")
        print(f"   Lines with [number]: {has_brackets}")
        print(f"   Lines mentioning nota/rujuk: {has_footnotes}")
except Exception as e:
    print("   Tanzil error:", e)

print("2. Checking Quran.com translation 39...")
qcom_url = "https://api.quran.com/api/v4/quran/translations/39"
req = urllib.request.Request(qcom_url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode('utf-8')
        has_sup = len(re.findall(r'<sup', content))
        has_bracket_nums = len(re.findall(r'\[\d+\]', content))
        print(f"   Quran.com translation 39 <sup> tags: {has_sup}")
        print(f"   Quran.com translation 39 [number] tags: {has_bracket_nums}")
except Exception as e:
    print("   Quran.com error:", e)
