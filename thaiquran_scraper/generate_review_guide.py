"""
Generate human-readable review markdown for all 87 flagged footnote placements.
"""

import csv
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REVIEW_CSV = os.path.join(BASE_DIR, "footnote_placement_review_needed.csv")
GUIDE_MD = os.path.join(BASE_DIR, "FOOTNOTE_PLACEMENT_REVIEW_GUIDE.md")

with open(REVIEW_CSV, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

# Group by Surah
by_surah = {}
for r in rows:
    by_surah.setdefault(int(r["surah"]), []).append(r)

lines = []
lines.append("# Footnote Placement Human Review Guide")
lines.append("")
lines.append(f"> **Audit Summary:** Out of 7,333 total footnotes, **7,246 (98.8%)** were automatically verified safe ($\Delta \le 7$ letters).")
lines.append(f"> This guide lists the remaining **{len(rows)} flagged items** where wording variations between the King Fahd translation and Arab Alumni translation caused a letter offset $> 7$ letters.")
lines.append("")
lines.append("---")
lines.append("")

for s_num in sorted(by_surah.keys()):
    items = by_surah[s_num]
    lines.append(f"## Surah {s_num} ({len(items)} items)")
    lines.append("")
    lines.append("| Ayah | FN # | $\Delta$ Letters | Target Position in Our Live Version | Commentary Snippet |")
    lines.append("| :---: | :---: | :---: | :--- | :--- |")
    for r in items:
        k = r["ayah_key"]
        fn = r["footnote_id"]
        d = r["letter_delta"]
        left = r["base_anchor_left"][-20:]
        right = r["base_anchor_right"][:20]
        snippet = r["footnote_snippet"][:60].replace("|", "\\|")
        placed_preview = f"...{left} **[{fn}]** {right}..."
        lines.append(f"| `{k}` | `{fn}` | `{d}` | {placed_preview} | {snippet} |")
    lines.append("")

with open(GUIDE_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Generated review guide with {len(rows)} items at {GUIDE_MD}")
