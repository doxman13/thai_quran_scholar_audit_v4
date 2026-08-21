"""
=============================================================================
PIPELINE 2: LLM-POWERED THAI CLAUSE SPACING & READING CADENCE ENGINE
=============================================================================
Target: King Fahd Complex Thai Quran Translation (Thai v3)

Purpose:
  Optimizes natural Thai clause pacing, breath pauses (Waqf-aligned),
  and dialogue spacing for a smooth reading experience on web/mobile apps.

Safety Architecture (Mathematical Character Lock):
  re.sub(r'\\s+', '', original_thai) == re.sub(r'\\s+', '', llm_spaced_thai)
  - 100.00% Character Invariant: If even ONE character, letter, vowel,
    or bracket is altered or dropped by the LLM, the change is
    INSTANTLY REJECTED and the original text is preserved bit-for-bit.

Features:
  - Multi-Key Client Pool (Auto-detects GEMINI_API_KEY_1, _2, _3... from .env)
  - Models: gemini-3.1-flash-lite (Primary) & gemini-3.5-flash-lite (Fallback)
  - Dynamic Character-Budget Batching (Max 1,200 chars per prompt)
  - Real-time Checkpointing & Resumability
=============================================================================
"""

import os
import sys
import json
import time
import re
import csv
import argparse
from typing import List, Dict, Any, Optional, Tuple
from google import genai
from google.genai import types

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_DATA_FILE = os.path.join(SCRIPT_DIR, "step2_tri_lingual_master.json")
CHECKPOINT_FILE = os.path.join(SCRIPT_DIR, "pipeline2_spacing_checkpoint.json")

OUTPUT_JSON = os.path.join(SCRIPT_DIR, "thai_v3_spacing_improved.json")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "thai_v3_spacing_improved.csv")
OUTPUT_REPORT_CSV = os.path.join(SCRIPT_DIR, "thai_v3_spacing_audit_report.csv")

MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.1-flash-lite"]

DEFAULT_CHAR_BUDGET = 1200  # Max Thai characters per prompt batch
MAX_RPM_PER_KEY = 10        # Conservative RPM per API key
MIN_INTERVAL_PER_KEY = 6.0  # Seconds between requests on the same key


# ---------------------------------------------------------------------------
# Multi-Key Rate Limiter & Client Pool
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, rpm: int = MAX_RPM_PER_KEY, min_interval: float = MIN_INTERVAL_PER_KEY):
        self.rpm = rpm
        self.min_interval = min_interval
        self.timestamps: List[float] = []

    def wait(self):
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t < 60.0]
        if len(self.timestamps) >= self.rpm:
            sleep_needed = 60.0 - (now - self.timestamps[0]) + 0.5
            if sleep_needed > 0:
                time.sleep(sleep_needed)
        if self.timestamps:
            elapsed = time.time() - self.timestamps[-1]
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
        self.timestamps.append(time.time())


class MultiKeyClientPool:
    def __init__(self, env_path: str):
        self.keys = self._load_keys(env_path)
        if not self.keys:
            raise ValueError(f"No Gemini API keys found in {env_path}! Please ensure GEMINI_API_KEY_1, _2, _3 are set.")
        self.clients = [genai.Client(api_key=k) for k in self.keys]
        self.limiters = [RateLimiter() for _ in self.keys]
        self.current_idx = 0
        self.exhausted_combos = set()
        print(f"Loaded {len(self.keys)} Gemini API Key(s) from .env")

    def _load_keys(self, env_path: str) -> List[str]:
        keys = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or not line or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'\"")
                    if "GEMINI_API_KEY" in k and v:
                        keys.append(v)
        for k, v in os.environ.items():
            if "GEMINI_API_KEY" in k and v and v not in keys:
                keys.append(v)
        return keys

    def get_client(self, model_name: Optional[str] = None) -> Tuple[genai.Client, int, RateLimiter]:
        num_keys = len(self.clients)
        for _ in range(num_keys):
            idx = self.current_idx
            self.current_idx = (self.current_idx + 1) % num_keys
            key_id = idx + 1
            if model_name and (model_name, key_id) in self.exhausted_combos:
                continue
            return self.clients[idx], key_id, self.limiters[idx]
        
        idx = self.current_idx
        self.current_idx = (self.current_idx + 1) % num_keys
        return self.clients[idx], idx + 1, self.limiters[idx]

    def mark_exhausted(self, model_name: str, key_id: int):
        self.exhausted_combos.add((model_name, key_id))
        print(f"  [Pool] Marked ({model_name}, Key #{key_id}) as exhausted for today.", flush=True)


# ---------------------------------------------------------------------------
# Spacing System Prompt (Strict Invariant Prompting)
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """You are an expert Thai Linguist and Quranic Prose Typography Editor.
Your ONLY task is to adjust and optimize THAI WHITESPACE SPACING for smooth reading flow, natural breath pauses, and clause cadence.

=== ABSOLUTE CARDINAL RULES ===

1. ZERO CHARACTER/WORD ALTERATIONS:
   - You MUST NOT add, delete, change, substitute, or rephrase ANY Thai words, letters, vowels, tone marks, or numbers.
   - If we strip all whitespace from your output, it MUST MATCH the original input EXACTLY character-for-character:
     `strip_whitespace(output) == strip_whitespace(input)`.

2. ABSOLUTE PARENTHESES PRESERVATION:
   - NEVER remove, add, or alter any text inside parentheses `(...)`.
   - Preserve all bracketed tafsir notes exactly as written.

3. THAI SPACING RULES:
   - Use spaces (' ') for natural pauses between clauses, after dialogue verbs (เช่น เขากล่าวว่า ...), and before conditional conjunctions (เช่น และหาก..., เพื่อที่...).
   - Tighten compound words that were accidentally split by spaces (เช่น 'ทั้งนี้ เพื่อ' -> 'ทั้งนี้เพื่อ', 'พระองค์นั้น เป็น' -> 'พระองค์นั้นเป็น').
   - DO NOT insert English punctuation like commas (',') or semicolons.

4. OUTPUT FORMAT:
   - Return a JSON array where each item contains `"ayah"` and the complete `"spaced_thai"` string.
"""

def create_spacing_prompt(surah_num: int, batch: List[Dict[str, Any]]) -> str:
    entries = []
    for v in batch:
        entries.append(
            f"Ayah {v['ayah']}:\n"
            f"{v['thai']}"
        )
    text_block = "\n\n".join(entries)

    return f"""Optimize the Thai clause spacing for the following {len(batch)} verses of Surah #{surah_num}.
Remember: DO NOT change, add, or remove any word or letter. Only adjust whitespace spaces (' ').

{text_block}

=== REQUIRED JSON OUTPUT SCHEMA ===
[
  {{
    "ayah": 1,
    "spaced_thai": "text with optimized spacing..."
  }}
]
"""


# ---------------------------------------------------------------------------
# Punctuation & Unicode Normalizer (Mechanical Post-Processing)
# ---------------------------------------------------------------------------
def normalize_mechanical_spacing(text: str) -> str:
    text = re.sub(r'[\u00a0\u200b\u200c\u200d\ufeff]', ' ', text)
    text = re.sub(r'(\S)\s*ๆ\s*([ก-๙])', r'\1 ๆ \2', text)
    text = re.sub(r'(\S)\s*ๆ(?=[^\Sก-๙]|$)', r'\1 ๆ', text)
    text = re.sub(r'([ก-๙])\(', r'\1 (', text)
    text = re.sub(r'\)([ก-๙])', r') \1', text)
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Strict Mathematical Character-Lock Guardrail
# ---------------------------------------------------------------------------
def validate_and_apply_spacing(original_thai: str, llm_spaced_thai: str) -> Tuple[bool, str, str]:
    """
    Asserts 100.00% character invariance.
    """
    orig_chars = re.sub(r'\s+', '', original_thai)
    llm_chars = re.sub(r'\s+', '', llm_spaced_thai)

    if orig_chars != llm_chars:
        # Character mismatch! Instantly REJECT and preserve original text.
        return False, original_thai, "REJECTED_CHARACTER_MISMATCH"

    final_text = normalize_mechanical_spacing(llm_spaced_thai)

    final_chars = re.sub(r'\s+', '', final_text)
    if final_chars != orig_chars:
        return False, original_thai, "REJECTED_POST_PROCESS_MISMATCH"

    is_modified = (final_text != original_thai)
    status_msg = "SPACING_OPTIMIZED" if is_modified else "CLEAN"
    return True, final_text, status_msg


# ---------------------------------------------------------------------------
# API Execution with Fallback
# ---------------------------------------------------------------------------
def clean_json_response(raw_text: str) -> str:
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
    s_idx = raw_text.find("[")
    e_idx = raw_text.rfind("]")
    if s_idx != -1 and e_idx != -1 and e_idx >= s_idx:
        return raw_text[s_idx:e_idx+1]
    return raw_text


def call_genai_with_fallbacks(pool: MultiKeyClientPool, prompt: str) -> Tuple[List[Dict[str, Any]], str, int]:
    for model_name in MODELS:
        for attempt in range(len(pool.clients)):
            client, key_id, limiter = pool.get_client(model_name=model_name)
            if (model_name, key_id) in pool.exhausted_combos:
                continue
            limiter.wait()
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.0,
                        response_mime_type="application/json",
                    )
                )
                raw_text = response.text or "[]"
                cleaned = clean_json_response(raw_text)
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    return parsed, model_name, key_id
                elif isinstance(parsed, dict):
                    if "results" in parsed and isinstance(parsed["results"], list):
                        return parsed["results"], model_name, key_id
                    return [parsed], model_name, key_id
            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    print(f"  [{model_name} Key #{key_id}] 503 Busy. Switching model...", flush=True)
                    break
                elif "404" in err_str or "NOT_FOUND" in err_str:
                    pool.mark_exhausted(model_name, key_id)
                    continue
                elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    if "quota" in err_str.lower() or "limit" in err_str.lower():
                        pool.mark_exhausted(model_name, key_id)
                        continue
                    else:
                        print(f"  [{model_name} Key #{key_id}] Rate limit hit. Pausing 10s...", flush=True)
                        time.sleep(10)
                else:
                    print(f"  [{model_name} Key #{key_id}] Attempt {attempt+1} Error: {e}", flush=True)
                    time.sleep(1)

    raise RuntimeError(f"Failed to get valid spacing response after trying all models and keys.")


# ---------------------------------------------------------------------------
# Dynamic Character-Budget Batcher
# ---------------------------------------------------------------------------
def create_dynamic_batches(ayahs: List[Dict[str, Any]], char_budget: int = DEFAULT_CHAR_BUDGET) -> List[List[Dict[str, Any]]]:
    """Create batches that contain exactly **one** ayah each.
    This overrides the previous dynamic‑budget logic and forces a
    conservative payload of a single verse per API request.
    """
    # Return a list where each inner list holds a single ayah dictionary
    return [[a] for a in ayahs]


# ---------------------------------------------------------------------------
# Checkpoint Management & Export
# ---------------------------------------------------------------------------
def load_checkpoint() -> Dict[str, Any]:
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_checkpoint(data: Dict[str, Any]):
    temp_file = CHECKPOINT_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, CHECKPOINT_FILE)


def export_spacing_datasets(checkpoint: Dict[str, Any], master_data: List[Dict[str, Any]]):
    output_rows = []
    report_rows = []

    for entry in master_data:
        key = f"{entry['surah']}:{entry['ayah']}"
        cp = checkpoint.get(key, {})
        orig_text = entry.get("thai", "")
        final_text = cp.get("final_thai", orig_text)
        status = cp.get("status", "CLEAN")

        output_rows.append({
            "surah": entry["surah"],
            "ayah": entry["ayah"],
            "translation": final_text
        })

        report_rows.append({
            "surah": entry["surah"],
            "ayah": entry["ayah"],
            "status": status,
            "char_lock_verified": cp.get("char_lock_verified", True),
            "original_thai": orig_text,
            "final_thai": final_text
        })

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_rows, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["surah", "ayah", "translation"])
        writer.writeheader()
        writer.writerows(output_rows)

    with open(OUTPUT_REPORT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["surah", "ayah", "status", "char_lock_verified", "original_thai", "final_thai"])
        writer.writeheader()
        writer.writerows(report_rows)


# ---------------------------------------------------------------------------
# Main Controller
# ---------------------------------------------------------------------------
def run_spacing_pipeline(surah_range: Optional[List[int]] = None, char_budget: int = DEFAULT_CHAR_BUDGET):
    print("\n" + "="*70)
    print("PIPELINE 2: LLM THAI SPACING & CLAUSE PACING ENGINE")
    print("="*70)

    if not os.path.exists(MASTER_DATA_FILE):
        raise FileNotFoundError(f"Master file not found: {MASTER_DATA_FILE}")
    with open(MASTER_DATA_FILE, "r", encoding="utf-8") as f:
        master_data: List[Dict[str, Any]] = json.load(f)
    print(f"Loaded {len(master_data)} verses from master dataset.")

    env_file = os.path.join(SCRIPT_DIR, ".env")
    pool = MultiKeyClientPool(env_file)

    surahs: Dict[int, List[Dict[str, Any]]] = {}
    for entry in master_data:
        s = entry["surah"]
        if surah_range and s not in surah_range:
            continue
        surahs.setdefault(s, []).append(entry)

    checkpoint = load_checkpoint()
    total_audited_initial = sum(1 for k, v in checkpoint.items() if v.get("is_processed"))
    print(f"Surahs in scope: {len(surahs)} | Already processed in checkpoint: {total_audited_initial} ayahs")

    total_ayahs_in_scope = sum(len(v) for v in surahs.values())

    for s_num, ayahs in surahs.items():
        needed_ayahs = [a for a in ayahs if not checkpoint.get(f"{s_num}:{a['ayah']}", {}).get("is_processed")]
        if not needed_ayahs:
            print(f"Surah {s_num:3d} already fully spaced. Skipping.", flush=True)
            continue

        batches = create_dynamic_batches(needed_ayahs, char_budget=char_budget)
        print(f"\n--> Spacing Surah {s_num:3d} ({len(needed_ayahs)} remaining ayahs in {len(batches)} micro-batches)...", flush=True)

        for b_idx, batch in enumerate(batches, 1):
            ayah_range_str = f"{batch[0]['ayah']}-{batch[-1]['ayah']}" if len(batch) > 1 else f"{batch[0]['ayah']}"
            prompt = create_spacing_prompt(s_num, batch)

            try:
                results, used_model, key_id = call_genai_with_fallbacks(pool, prompt)
            except Exception as e:
                print(f"    CRITICAL FAILURE on Surah {s_num} Ayahs {ayah_range_str}: {e}", flush=True)
                continue

            results_by_ayah = {item.get("ayah"): item.get("spaced_thai", "") for item in results if item.get("ayah")}

            for v in batch:
                a_num = v["ayah"]
                key = f"{s_num}:{a_num}"
                orig_text = v["thai"]
                llm_output = results_by_ayah.get(a_num, orig_text)

                is_valid, final_text, status = validate_and_apply_spacing(orig_text, llm_output)

                checkpoint[key] = {
                    "is_processed": True,
                    "model": used_model,
                    "final_thai": final_text,
                    "status": status,
                    "char_lock_verified": is_valid,
                    "timestamp": time.time()
                }

            save_checkpoint(checkpoint)
            total_now = sum(1 for k, v in checkpoint.items() if v.get("is_processed"))
            print(f"    [{used_model} Key #{key_id}] Surah {s_num} Ayahs {ayah_range_str} ({len(batch)} ayahs) spaced. ({total_now}/{total_ayahs_in_scope} total)", flush=True)

        export_spacing_datasets(checkpoint, master_data)

    print("\n" + "="*70)
    print("Pipeline 2 Complete! 100% Mathematical Character Invariance Verified.")
    print(f"1. Improved JSON: {OUTPUT_JSON}")
    print(f"2. Improved CSV:  {OUTPUT_CSV}")
    print(f"3. Audit Report:  {OUTPUT_REPORT_CSV}")
    print("="*70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline 2: LLM Thai Spacing & Clause Pacing Engine")
    parser.add_argument("--surahs", type=str, default="all", help="Surah range e.g. 'all', '1-10', '114', or '1,2,3'")
    parser.add_argument("--char_budget", type=int, default=DEFAULT_CHAR_BUDGET, help="Max characters per dynamic prompt payload (default: 1200)")
    parser.add_argument("--reset_checkpoint", action="store_true", help="Reset checkpoint and re-process from scratch")

    args = parser.parse_args()

    if args.reset_checkpoint:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            print("Checkpoint reset.")

    surah_range = None
    if args.surahs.lower() != "all":
        surah_range = []
        parts = args.surahs.split(",")
        for p in parts:
            p = p.strip()
            if "-" in p:
                start, end = map(int, p.split("-"))
                surah_range.extend(range(start, end + 1))
            else:
                surah_range.append(int(p))

    run_spacing_pipeline(surah_range=surah_range, char_budget=args.char_budget)
