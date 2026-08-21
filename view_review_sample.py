import csv
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

csv_file = r"H:\gits\thai_quran_scholar_audit_v4\pipeline1_human_review.csv"
with open(csv_file, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total CSV Review Rows: {len(rows)}")
print("\nSample 8 findings:")
for r in rows[:8]:
    print(f"[{r['surah']}:{r['ayah']}] Issue: {r['issue_type']} | Status: {r['guardrail_status']}")
    print(f"   Target     : {r['target_phrase']}")
    print(f"   Replacement: {r['replacement_phrase']}")
    print(f"   Reason     : {r['explanation']}")
    print("-" * 60)
