# ThaiQuran Scraper & Commentary Analysis

Production-grade pipeline to scrape, structure, validate, and compare Thai Quran translations and explanatory footnotes from [ThaiQuran.com](https://www.thaiquran.com).

---

## 1. Project Directory Structure

```text
thaiquran_scraper/
├── scrape_thaiquran.py       # Main robust scraping script with retries, jitter, and checkpointing
├── validate_dataset.py       # Quality assurance auditor verifying 114 Surahs & 6,236 Ayahs
├── checkpoint_progress.json  # Live checkpoint state for safe resumption if interrupted
├── quran_thai_by_surah.json  # Complete structured JSON deliverable
├── quran_thai.csv            # Flattened CSV deliverable (columns: surah, ayah, ayah_key, translation, footnotes)
└── README.md                 # Documentation and execution roadmap
```

---

## 2. Scraping Architecture & Technical Specifications

| Parameter | Specification |
| :--- | :--- |
| **Target URL Pattern** | `https://www.thaiquran.com/chapter/{surah_number}?showTranslation=1&showComment=1` |
| **Surah Range** | Sequential iteration from `1` to `114` (all 6,236 Ayahs) |
| **HTTP Engine** | `requests.Session` with persistent browser headers (`User-Agent`, `Accept-Language: th,en-US`) |
| **Retry & Resilience** | Exponential backoff (up to 3 retries) on HTTP 429, 5xx errors, and network timeouts |
| **Rate Limiting** | Respectful jitter delay (0.8 to 1.5 seconds) between Surah requests |
| **HTML Parsing Engine** | `BeautifulSoup` targeting Livewire DOM nodes (`wire:key="quran-X"`) |
| **Text Sanitization** | Regex stripping for `Translation :` and `Comment :` prefixes, normalization of spacing |
| **Crash Recovery** | Automatic progress checkpoints saved every 5 Surahs and on interrupt |

---

## 3. Data Schema

### JSON Format (`quran_thai_by_surah.json`)
```json
[
  {
    "surah_number": 1,
    "ayah_count": 7,
    "ayahs": [
      {
        "surah_number": 1,
        "ayah_number": 4,
        "ayah_key": "1:4",
        "translation": "ผู้ทรงอภิสิทธิ์แห่งวันตอบแทน(1)",
        "footnotes": [
          "(1)คือวันปรโลก อันเป็นวันที่มนุษย์ฟื้นคืนชีพมาเพื่อรับการตอบแทน"
        ]
      }
    ]
  }
]
```

### CSV Format (`quran_thai.csv`)
- **Encoding**: UTF-8 with BOM (`utf-8-sig`) for native compatibility with Microsoft Excel without Thai character corruption.
- **Columns**: `surah`, `ayah`, `ayah_key`, `translation`, `footnotes`
- **Footnotes delimiter**: Multiple footnotes within an Ayah are concatenated using ` | `.

---

## 4. How to Run

### Run Full Quran Scrape (Surahs 1 to 114):
```bash
python scrape_thaiquran.py
```
*(Estimated duration: ~3 to 4 minutes with polite delays)*

### Resume Scraping if Interrupted:
The scraper automatically detects `checkpoint_progress.json` and continues from the next unscraped Surah:
```bash
python scrape_thaiquran.py
```

### Run Custom Range (e.g., Testing or Re-scraping specific Surahs):
```bash
python scrape_thaiquran.py --start 1 --end 10 --no-resume
```

### Validate Dataset Completeness:
```bash
python validate_dataset.py
```

---

## 5. Next Steps: Cross-Translation Audit & Commentary Integration

1. **Phase 1 (Current)**: Complete full scrape of all 114 Surahs and 6,236 Ayahs.
2. **Phase 2 (Translation Comparison)**:
   - Compare ThaiQuran translations against our existing baseline datasets (`quran_foundation_thai_structured.json` / `thai_v3_spacing_improved.json`).
   - Identify orthographic differences (e.g., `อัลลอฮ์` vs `อัลลอฮฺ`, punctuation conventions, spacing nuances).
   - Detect whether ThaiQuran.com represents the King Fahd Complex translation, Sheikh Ismail bin Qasim, or another scholarly translation.
3. **Phase 3 (Commentary Utilization)**:
   - Extract commentary for verses with active theological debates or subtle linguistic nuances.
   - Cross-reference commentary notes with our audit findings in `pipeline1_audit_findings.csv` to enrich context and scholarly citations.
