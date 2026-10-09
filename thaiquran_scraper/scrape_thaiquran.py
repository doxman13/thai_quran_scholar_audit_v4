"""
Production-Ready Scraper for ThaiQuran (https://www.thaiquran.com)
Extracts Thai Quran translations and footnotes/commentaries for all 114 Surahs.

Outputs:
  - thaiquran_scraper/quran_thai_by_surah.json
  - thaiquran_scraper/quran_thai.csv
  - thaiquran_scraper/checkpoint_progress.json
"""

import csv
import json
import logging
import os
import random
import re
import sys
import time
from typing import Any, Dict, List, Optional
import requests
from bs4 import BeautifulSoup

# Ensure UTF-8 output across Windows environments
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ThaiQuranScraper")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_OUTPUT_PATH = os.path.join(BASE_DIR, "quran_thai_by_surah.json")
CSV_OUTPUT_PATH = os.path.join(BASE_DIR, "quran_thai.csv")
CHECKPOINT_PATH = os.path.join(BASE_DIR, "checkpoint_progress.json")

BASE_URL = "https://www.thaiquran.com/chapter/{surah_number}?showTranslation=1&showComment=1"
TOTAL_SURAHS = 114

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "th,en-US;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}


def clean_text(text: str) -> str:
    """Normalize whitespace and remove redundant spaces/newlines."""
    if not text:
        return ""
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n", text)
    return text.strip()


def parse_surah_html(html_content: str, surah_number: int) -> List[Dict[str, Any]]:
    """
    Parses the Surah HTML page and extracts all verses, translations, and footnotes.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Locate all verse containers via Livewire wire:key="quran-{index}"
    verse_containers = soup.find_all("div", attrs={"wire:key": lambda x: x and x.startswith("quran-")})
    
    # Fallback to border-gold-400 parent containers if wire:key is modified
    if not verse_containers:
        verse_containers = soup.find_all("div", class_=lambda c: c and "border-gold-400" in c)

    ayah_list = []

    for container in verse_containers:
        # 1. Extract Ayah Key (e.g. '1:1', '2:255')
        key_tag = container.find("p", class_=lambda c: c and "tracking-tight" in c and "font-extrabold" in c)
        key_text = key_tag.get_text(strip=True) if key_tag else ""
        
        match = re.search(r"(\d+):(\d+)", key_text)
        if match:
            s_num = int(match.group(1))
            a_num = int(match.group(2))
            ayah_key = f"{s_num}:{a_num}"
        else:
            # Fallback search anywhere in the container
            fallback_match = re.search(r"\b" + str(surah_number) + r":(\d+)\b", container.get_text())
            if fallback_match:
                s_num = surah_number
                a_num = int(fallback_match.group(1))
                ayah_key = f"{s_num}:{a_num}"
            else:
                continue

        # 2. Extract Translation
        # HTML tag: <span class="font-extrabold ...">Translation</span>: ...
        trans_span = container.find("span", string=re.compile(r"^\s*Translation\s*$", re.I))
        if trans_span and trans_span.parent:
            raw_p = trans_span.parent.get_text()
            translation_text = re.sub(r"^\s*Translation\s*:\s*", "", raw_p, flags=re.I)
            translation_text = clean_text(translation_text)
        else:
            trans_p = container.find(lambda tag: tag.name == "p" and "Translation :" in tag.get_text())
            if trans_p:
                translation_text = clean_text(trans_p.get_text().split("Translation :", 1)[-1])
            else:
                translation_text = ""

        # 3. Extract Footnotes / Commentary
        # HTML tag: <span class="font-extrabold ...">Comment</span>: (1)...
        comment_spans = container.find_all("span", string=re.compile(r"^\s*Comment\s*$", re.I))
        footnotes = []
        for c_span in comment_spans:
            if c_span.parent:
                raw_cp = c_span.parent.get_text()
                comment_text = re.sub(r"^\s*Comment\s*:\s*", "", raw_cp, flags=re.I)
                comment_text = clean_text(comment_text)
                if comment_text:
                    footnotes.append(comment_text)

        ayah_list.append({
            "surah_number": s_num,
            "ayah_number": a_num,
            "ayah_key": ayah_key,
            "translation": translation_text,
            "footnotes": footnotes,
        })

    # Sort verses by ayah_number to ensure strict sequential order
    ayah_list.sort(key=lambda x: x["ayah_number"])
    return ayah_list


def fetch_surah_with_retry(
    session: requests.Session,
    surah_number: int,
    max_retries: int = 3,
    base_timeout: float = 25.0,
) -> Optional[str]:
    """
    Fetches a Surah page with automatic retry logic and exponential backoff.
    """
    url = BASE_URL.format(surah_number=surah_number)
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, timeout=base_timeout)
            if response.status_code == 200:
                return response.text
            elif response.status_code in (429, 500, 502, 503, 504):
                sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                logger.warning(
                    f"HTTP {response.status_code} for Surah {surah_number}. "
                    f"Retry {attempt}/{max_retries} after {sleep_time:.1f}s..."
                )
                time.sleep(sleep_time)
            else:
                logger.error(f"Unrecoverable HTTP {response.status_code} for Surah {surah_number}: {url}")
                return None
        except (requests.RequestException, requests.Timeout) as e:
            sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
            logger.warning(
                f"Network error on Surah {surah_number} (Attempt {attempt}/{max_retries}): {e}. "
                f"Retrying in {sleep_time:.1f}s..."
            )
            time.sleep(sleep_time)

    logger.error(f"Failed to fetch Surah {surah_number} after {max_retries} attempts.")
    return None


def save_checkpoint(surahs_data: Dict[str, Any]) -> None:
    """Save progress checkpoint to allow seamless resumption."""
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(surahs_data, f, ensure_ascii=False, indent=2)


def load_checkpoint() -> Dict[str, Any]:
    """Load existing progress checkpoint if present."""
    if os.path.exists(CHECKPOINT_PATH):
        try:
            with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"Loaded checkpoint with {len(data)} completed surahs.")
                return data
        except Exception as e:
            logger.warning(f"Failed to read checkpoint: {e}. Starting fresh.")
    return {}


def export_deliverables(
    surahs_dict: Dict[str, Any],
    expected_start: int = 1,
    expected_end: int = TOTAL_SURAHS,
) -> None:
    """Exports both JSON and CSV deliverables."""
    ordered_surahs = []
    total_ayahs = 0
    total_footnotes = 0
    csv_rows = []

    # Sort available surah keys numerically
    available_nums = sorted([int(k) for k in surahs_dict.keys()])

    for s_num in available_nums:
        surah_entry = surahs_dict[str(s_num)]
        ordered_surahs.append(surah_entry)
        ayahs = surah_entry.get("ayahs", [])
        total_ayahs += len(ayahs)
        for ayah in ayahs:
            notes = ayah.get("footnotes", [])
            total_footnotes += len(notes)
            csv_rows.append({
                "surah": ayah["surah_number"],
                "ayah": ayah["ayah_number"],
                "ayah_key": ayah["ayah_key"],
                "translation": ayah["translation"],
                "footnotes": " | ".join(notes),
            })

    # Report any missing surahs within the expected range
    missing = [s for s in range(expected_start, expected_end + 1) if str(s) not in surahs_dict]
    if missing:
        logger.warning(f"Surahs missing from expected range [{expected_start}-{expected_end}]: {missing}")

    # 1. Write JSON Deliverable
    logger.info(f"Saving {len(ordered_surahs)} Surahs ({total_ayahs} Ayahs) to {JSON_OUTPUT_PATH}...")
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(ordered_surahs, f, ensure_ascii=False, indent=2)

    # 2. Write CSV Deliverable (utf-8-sig ensures proper display in Excel)
    logger.info(f"Saving {len(csv_rows)} rows to {CSV_OUTPUT_PATH}...")
    with open(CSV_OUTPUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["surah", "ayah", "ayah_key", "translation", "footnotes"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    logger.info("=" * 60)
    logger.info("SCRAPING AND EXPORT SUMMARY")
    logger.info(f"Surahs in dataset:     {len(ordered_surahs)}/{TOTAL_SURAHS}")
    logger.info(f"Total Ayahs extracted: {total_ayahs}")
    logger.info(f"Total Footnotes:       {total_footnotes}")
    logger.info(f"JSON: {JSON_OUTPUT_PATH}")
    logger.info(f"CSV:  {CSV_OUTPUT_PATH}")
    logger.info("=" * 60)


def run_scraper(
    start_surah: int = 1,
    end_surah: int = TOTAL_SURAHS,
    resume: bool = True,
) -> None:
    """Main execution function for scraping ThaiQuran."""
    logger.info("=" * 60)
    logger.info("ThaiQuran.com Scraper Initialized")
    logger.info(f"Target Surah Range: {start_surah} to {end_surah}")
    logger.info(f"Resume Mode: {'Enabled' if resume else 'Disabled'}")
    logger.info("=" * 60)

    surahs_data = load_checkpoint() if resume else {}

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    try:
        for s_num in range(start_surah, end_surah + 1):
            s_key = str(s_num)
            if resume and s_key in surahs_data and len(surahs_data[s_key].get("ayahs", [])) > 0:
                logger.info(f"[Surah {s_num}/{TOTAL_SURAHS}] Already scraped ({len(surahs_data[s_key]['ayahs'])} ayahs) - Skipping.")
                continue

            html = fetch_surah_with_retry(session, s_num)
            if not html:
                logger.error(f"[Surah {s_num}/{TOTAL_SURAHS}] FAILED to retrieve HTML.")
                continue

            ayahs = parse_surah_html(html, s_num)
            surahs_data[s_key] = {
                "surah_number": s_num,
                "ayah_count": len(ayahs),
                "ayahs": ayahs,
            }

            logger.info(f"[Surah {s_num}/{TOTAL_SURAHS}] Extracted {len(ayahs)} ayahs")

            # Checkpoint every 5 surahs or at the end
            if s_num % 5 == 0 or s_num == end_surah:
                save_checkpoint(surahs_data)

            # Respectful jitter delay between 0.8s and 1.5s
            if s_num < end_surah:
                delay = random.uniform(0.8, 1.5)
                time.sleep(delay)

    except KeyboardInterrupt:
        logger.warning("\nScraping interrupted by user. Saving current checkpoint...")
        save_checkpoint(surahs_data)
        logger.info("Checkpoint saved. Re-run script to resume seamlessly.")
        return

    # Final save and export
    save_checkpoint(surahs_data)
    export_deliverables(surahs_data, expected_start=start_surah, expected_end=end_surah)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scrape Thai Quran translations and footnotes.")
    parser.add_argument("--start", type=int, default=1, help="Starting surah (1-114)")
    parser.add_argument("--end", type=int, default=114, help="Ending surah (1-114)")
    parser.add_argument("--no-resume", action="store_true", help="Do not load checkpoint, start fresh")
    args = parser.parse_args()

    run_scraper(
        start_surah=args.start,
        end_surah=args.end,
        resume=not args.no_resume,
    )
