# Audit & Spacing Progress Log

**Date:** 2026-08-21  
**Repository:** thai_quran_scholar_audit_v4  

---

## 1. Pipeline 1: Theological & Scholarship Auditor (Completed 100%)
- **Scope:** Audited all 6,236 Ayahs of the Quran using multi-model Gemini fallbacks across 6 API keys.
- **Completion:** 6,236 / 6,236 Ayahs (100%).
- **Outputs Generated:**
  - `pipeline1_human_review.csv` (1,309 flagged items categorized by typo, particle, or meaning precision)
  - `pipeline1_audit_findings.csv`
  - `pipeline1_audit_checkpoint.json`

---

## 2. Pipeline 2: LLM Thai Spacing & Clause Cadence Engine (In Progress — 68.5% Base, 92.3% Refined)
- **Mode:** Single-verse micro-batching (`[[a] for a in ayahs]`) with strict NFC Unicode normalized mathematical character-lock.
- **Engine Pool:** 6 Gemini API keys with multi-model fallback (`gemini-3.5-flash-lite`, `gemini-2.5-flash`, `gemini-3.1-flash-lite`).
- **Target Refinement (`--refine_targets`):**
  - **Refined with Upgraded Prompt (`v2_nfc`):** 1,692 / 1,834 targeted ayahs (92.3% of targeted scope).
  - Fixed over-segmentation around `แห่ง`, `ของ`, `เป็น`, `คือ`, `ว่า`, `เพื่อ`, and `ผู้ทรง...`.
  - Resolved false-positive character mismatches with NFC Unicode normalization.
- **Current Status Breakdown (across 4,270 audited ayahs in checkpoint):**
  - `CLEAN` (spacing optimal & natural): **3,158 Ayahs**
  - `SPACING_OPTIMIZED` (cadence & dialogue pauses): **1,007 Ayahs**
  - `REJECTED_CHARACTER_MISMATCH` (safely preserved bit-for-bit): **105 Ayahs** (reduced from 262)
- **Datasets Updated in Real-Time:**
  - `thai_v3_spacing_improved.json`
  - `thai_v3_spacing_improved.csv`
  - `thai_v3_spacing_audit_report.csv`
  - `pipeline2_spacing_checkpoint.json`

---

## Next Steps for Tomorrow (or after quota reset)
1. Run `python pipeline2_llm_spacing_normalizer.py --refine_targets both` to complete the remaining ~142 unrefined targets in Surahs 39–42.
2. Run `python pipeline2_llm_spacing_normalizer.py --surahs all` to process the remaining 1,966 Ayahs (Surahs 42–114) to achieve 100% full Quran coverage.
