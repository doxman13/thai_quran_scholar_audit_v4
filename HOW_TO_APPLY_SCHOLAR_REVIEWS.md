# Thai Quran Translation — Scholar Audit Review & Update Guide

> **Important Reference Note:** This document explains how to review, approve, and apply theological updates from **Pipeline 1** across the entire Thai Quran ecosystem (`thai_quran_scholar_audit_v4`, `thai-quran-app`, and `thai-quran-web`).

---

## 1. Where to Do the Review

Open the review spreadsheet located at:
📁 **[`final_files/06_pipeline1_theological_scholarship_review.csv`](file:///H:/gits/thai_quran_scholar_audit_v4/final_files/06_pipeline1_theological_scholarship_review.csv)**

### Columns Overview
| Column | Description |
| :--- | :--- |
| `surah`, `ayah` | Verse identification (e.g. Surah 2, Ayah 255) |
| `issue_type` | `MISTRANSLATION`, `THEOLOGICAL_DRIFT`, or `TYPO` |
| `explanation` | Detailed scholarly explanation of the issue |
| `target_phrase` | The problematic Thai phrase |
| `replacement_phrase` | The recommended theological replacement |
| `original_thai` | Current master Thai translation |
| `proposed_thai` | Full verse with the correction applied |
| `arabic_anchor` / `arabic_text` | Classical Arabic Quranic reference words |
| `malay_reference` | Standard Tafsir Pimpinan Ar-Rahman anchor |
| **`reviewer_decision`** | **👉 The ONLY column you need to fill in!** |

---

## 2. How to Fill in `reviewer_decision`

For each row in the CSV, enter your choice in the **`reviewer_decision`** column:

1. **To Approve the Proposed Fix:**
   - Type **`APPROVED`** (or `ACCEPT` / `YES`).
   - *Result:* The automated script will replace the verse with `proposed_thai`.

2. **To Reject the Proposed Fix (Keep Current Translation):**
   - Type **`REJECTED`** (or `REJECT` / `NO` or leave blank).
   - *Result:* The verse will remain 100% unchanged.

3. **To Use a Custom Scholar Revision:**
   - Type your **custom Thai sentence** directly in the `reviewer_decision` cell.
   - *Result:* The automated script will use your exact custom translation.

---

## 3. How to Apply the Updates (1-Click Command)

Once you or the scholar finish filling in the decisions in the CSV:

1. Open PowerShell / Terminal in `H:\gits\thai_quran_scholar_audit_v4`:
```powershell
python scripts/apply_pipeline1_reviews.py
```

### What the script does automatically:
- ✅ **Sanitizes Typography:** Strips any accidental Western punctuation (`.`, `,`, `?`, `!`, `"`, `-`), collapses redundant spaces, and ensures 100% Thai typography compliance (preserving Phinthu `ฺ`, Maiyamok `ๆ`, and parentheses `()`).
- ✅ **Updates Master Repositories:** Updates `01_thai_quran_translation_v3_master.json` and `02_thai_quran_translation_v3_master.csv`.
- ✅ **Appends to Audit Transparency Log:** Adds approved fixes with notes to `05_thai_translation_fixes_and_audit_log.csv`.
- ✅ **Updates Mobile App (`thai-quran-app`):**
  - Updates `assets/thai_v3.json`
  - Updates `translation_th` in SQLite `assets/quran_offline.db`
  - Auto-increments SQLite `PRAGMA user_version` and Dart `_targetDbVersion` so installed mobile devices automatically refresh on next launch.
- ✅ **Updates Web App (`thai-quran-web`):**
  - Updates `src/data/thai_v3.json`
  - Copies latest transparency audit log to `src/data/`
  - Automatically runs `export_db_for_web.py` to regenerate all 114 Word-by-Word JSONs.
- ✅ **Updates Supabase Cloud Storage & Version Manifest:**
  - Uploads latest `thai_v3.json` directly to Supabase Storage (`app-content/thai_v3.json`).
  - Auto-increments `app_content_versions` table version so live web clients immediately fetch the newest translation.


---

## 4. Final Verification & Deployment

After running the script:

### A. Mobile App (`thai-quran-app`)
```powershell
cd H:\gits\thai-quran-app
git add .
git commit -m "feat: apply approved scholar audit theological corrections"
git push
```

### B. Web App (`thai-quran-web`)
```powershell
cd H:\gits\thai-quran-web
npm run build
git add .
git commit -m "feat: apply approved scholar audit theological corrections and sync WBW"
git push
```

---

## 5. File Inventory Quick Reference

| System | Target File | Purpose |
| :--- | :--- | :--- |
| **Audit Repo** | `final_files/01_thai_quran_translation_v3_master.json` | Master Source of Truth (JSON) |
| **Audit Repo** | `final_files/02_thai_quran_translation_v3_master.csv` | Master Source of Truth (CSV) |
| **Audit Repo** | `final_files/05_thai_translation_fixes_and_audit_log.csv` | Public Audit & Transparency Log |
| **Audit Repo** | `final_files/06_pipeline1_theological_scholarship_review.csv` | **Reviewer Input Sheet** |
| **Mobile App** | `thai-quran-app/assets/quran_offline.db` | Offline SQLite database (`verses.translation_th`) |
| **Mobile App** | `thai-quran-app/assets/thai_v3.json` | Fast memory key-value translation map |
| **Mobile App** | `thai-quran-app/lib/services/offline_quran_database_service.dart` | Database schema version bumper |
| **Web App** | `thai-quran-web/src/data/thai_v3.json` | Nested web translation dataset |
| **Web App** | `thai-quran-web/src/data/thai_translation_fixes_and_audit_log.csv` | Public website audit log dataset |
| **Web App** | `thai-quran-web/public/data/wbw/*.json` | Word-by-Word segmented datasets (114 Surahs) |
