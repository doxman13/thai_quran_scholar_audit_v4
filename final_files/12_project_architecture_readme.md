# Thai Quran Scholar Audit & Spacing Engine (v4)

> **Dedicated Workspace:** `H:\gits\thai_quran_scholar_audit_v4`  
> **Master Dataset:** King Fahd Complex Thai Quran Translation (`step2_tri_lingual_master.json` - 6,236 Ayahs)  
> **Source of Truth:** Arabic Uthmani Text (`المتن الأصلي`)  
> **Regional Cross-Reference:** Malay Basmeih (*Tafsir Pimpinan Ar-Rahman*)  
> **Architecture:** Clean Separation of Concerns into Two Independent, Fault-Tolerant Pipelines.

---

## Architecture Summary

```
                       ┌────────────────────────────────────────────────────────────┐
                       │    King Fahd Complex Thai Quran Translation (Thai v3)      │
                       └─────────────────────────────┬──────────────────────────────┘
                                                     │
                       ┌─────────────────────────────┴──────────────────────────────┐
                       │                                                            │
                       ▼                                                            ▼
┌─────────────────────────────────────────────┐    ┌─────────────────────────────────────────────┐
│ PIPELINE 1: Theological & Typo Auditor      │    │ PIPELINE 2: LLM Clause Spacing Engine       │
│ (`pipeline1_theological_auditor.py`)        │    │ (`pipeline2_llm_spacing_normalizer.py`)     │
├─────────────────────────────────────────────┤    ├─────────────────────────────────────────────┤
│ • Cross-audits Arabic + Malay vs Thai       │    │ • Optimizes clause pauses, Waqf pacing,     │
│ • Focus: Typos, math errors, reversed       │    │   dialogue spacing, compound words.         │
│   pronouns, omitted Arabic clauses.         │    │ • Safety: Strict Mathematical Character     │
│ • Schema: Exact Substring Diffs only        │    │   Lock `strip_space(orig) == strip(llm)`.   │
│   (`target_phrase` -> `replacement`).       │    │ • 100.00% Character Invariant: ZERO words   │
│ • ZERO SPACING: Never touches whitespace.   │    │   or parenthetical notes can be altered.    │
└─────────────────────────────────────────────┘    └─────────────────────────────────────────────┘
```

---

## Multi-Key Configuration (`.env`)

The `.env` file in this directory contains all 3 API keys:
```env
GEMINI_API_KEY_1="AIzaSyFirstKey..."
GEMINI_API_KEY_2="AIzaSySecondKey..."
GEMINI_API_KEY_3="AIzaSyThirdKey..."
```

* **Quota:** ~4,500 RPD total.
* **Per-Pipeline Requirement:** ~1,000 requests for all 6,236 Ayahs.
* **Load Per Key:** Only ~330 requests per key (under 25% of daily quota).

---

## Execution Guide

### Running Pipeline 1 (Theological & Typo Audit)
```powershell
# Run full Quran
python pipeline1_theological_auditor.py --surahs all

# Run specific Surahs (e.g. 1 to 10)
python pipeline1_theological_auditor.py --surahs 1-10

# Reset checkpoint and re-audit
python pipeline1_theological_auditor.py --reset_checkpoint
```
* **Output 1:** `pipeline1_audit_findings.csv` (Detailed audit log)
* **Output 2:** `pipeline1_human_review.csv` (Spreadsheet for manual approval)
* **Checkpoint:** `pipeline1_audit_checkpoint.json`

### Running Pipeline 2 (LLM Clause Spacing & Reading Cadence)
```powershell
# Run full Quran
python pipeline2_llm_spacing_normalizer.py --surahs all

# Run specific Surahs (e.g. 1 to 10)
python pipeline2_llm_spacing_normalizer.py --surahs 1-10

# Reset checkpoint and re-process
python pipeline2_llm_spacing_normalizer.py --reset_checkpoint
```
* **Output 1:** `thai_v3_spacing_improved.json`
* **Output 2:** `thai_v3_spacing_improved.csv`
* **Output 3:** `thai_v3_spacing_audit_report.csv`
* **Checkpoint:** `pipeline2_spacing_checkpoint.json`

---

## Mathematical Safety Verification

Both pipelines enforce mathematical invariants before saving any verse:
1. **Pipeline 1:** Substring verification (`target_phrase in original_thai`) + Bracket lock + Delta threshold.
2. **Pipeline 2:** Full character lock (`re.sub(r'\s+', '', orig) == re.sub(r'\s+', '', llm_out)`). If even 1 character/bracket differs, the modification is automatically rejected.
