import json
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

cp_file = r"H:\gits\thai_quran_scholar_audit_v4\pipeline1_audit_checkpoint.json"
try:
    with open(cp_file, "r", encoding="utf-8") as f:
        cp = json.load(f)
except Exception as e:
    print("Checkpoint loading error:", e)
    sys.exit(0)

print(f"Total entries in checkpoint: {len(cp)}")
for k, v in cp.items():
    if v.get("findings"):
        for item in v["findings"]:
            print(f"[{k}] {item.get('issue_type')} | Guardrail: {item.get('guardrail_status')}")
            print(f"   Target : {item.get('target_phrase')}")
            print(f"   Repl   : {item.get('replacement_phrase')}")
            print(f"   Reason : {item.get('reason_explanation')}")
            print("-" * 50)
