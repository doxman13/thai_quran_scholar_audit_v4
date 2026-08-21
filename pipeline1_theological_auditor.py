"""
=============================================================================
PIPELINE 1: SCHOLAR AUDITOR v4 — THEOLOGICAL & TYPO AUDIT ENGINE
=============================================================================
Target: King Fahd Complex Thai Quran Translation (Thai v3 Clean Master)
Anchors:
  1. Arabic Uthmani Text (المتن الأصلي - Source of Truth)
  2. Malay Quran Translation (Tafsir Pimpinan Ar-Rahman / Abdullah Muhammad Basmeih)
  3. Thai v3 Clean Master

Scope:
  - Audits exclusively for genuine typos, spelling mistakes, print math errors,
    reversed pronouns, omitted Arabic clauses, and false cognates.
  - ZERO SPACING INTERFERENCE: Spacing is 100% decoupled into Pipeline 2.
  - TARGETED DIFFS ONLY: The model never rewrites the verse; it only outputs
    exact substrings to replace.

Safety Invariants:
  - Substring Verification: target_phrase must exist verbatim in master text.
  - Parenthetical Tafsir Lock: All (...) notes are protected from removal.
  - Length Delta Threshold: Typo fixes cannot alter length by > 15 chars.
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
# Paths & Settings
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_DATA_FILE = os.path.join(SCRIPT_DIR, "step2_tri_lingual_master.json")
CHECKPOINT_FILE = os.path.join(SCRIPT_DIR, "pipeline1_audit_checkpoint.json")

OUTPUT_REPORT_CSV = os.path.join(SCRIPT_DIR, "pipeline1_audit_findings.csv")
OUTPUT_REVIEW_CSV = os.path.join(SCRIPT_DIR, "pipeline1_human_review.csv")
MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.1-flash-lite"]

DEFAULT_CHAR_BUDGET = 1000  # Max Thai characters per prompt batch
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
        self.exhausted_combos = set()  # (model_name, key_id)
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
        
        # If all keys exhausted for this model, return next index anyway
        idx = self.current_idx
        self.current_idx = (self.current_idx + 1) % num_keys
        return self.clients[idx], idx + 1, self.limiters[idx]

    def mark_exhausted(self, model_name: str, key_id: int):
        self.exhausted_combos.add((model_name, key_id))
        print(f"  [Pool] Marked ({model_name}, Key #{key_id}) as exhausted for today.", flush=True)


# ---------------------------------------------------------------------------
# Scholar System Instruction
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = """You are a Grand Master Quranic Arabic-Thai Lexicographer and Senior Proofreader for the King Fahd Complex for the Printing of the Holy Quran.

Your sole duty is to inspect the King Fahd Complex Thai Quran Translation (Thai v3) against the original Arabic text (`المتن الأصلي`) and regional Malay cross-reference (`Tafsir Pimpinan Ar-Rahman by Abdullah Basmeih`).

=== MISSION GOALS & AUDIT SCOPE ===

1. SCAN FOR CONCRETE THEOLOGICAL & LINGUISTIC FLAWS ONLY:
   - Severe mistranslations that distort the Islamic Aqeedah, Tawheed, or original Arabic meaning.
   - Omitted Arabic clauses, forgotten prepositions, or dropped sentences.
   - Reversed pronouns (e.g. translated as 'he' when Arabic refers to 'they' or 'We/Allah').
   - Numerical / mathematical errors (e.g. 'พันปี' vs 'ห้าหมื่นปี').
   - Thai typographical errors, misspellings, vowel collisions, or repeated words.

2. ABSOLUTE CONSERVATIVE PROTOCOL:
   - The King Fahd translation is an official, established Islamic text.
   - DO NOT suggest stylistic alternatives, flow improvements, synonymous rewording, or modernization.
   - If a Thai sentence is grammatically and theologically acceptable, YOU MUST RETURN AN EMPTY ARRAY: `[]`.
   - Silence on perfection: Over 90% of verses are expected to return NO corrections.

3. ZERO SPACING / PUNCTUATION INTERFERENCE:
   - DO NOT flag or modify whitespace, spaces, indents, or line breaks.
   - DO NOT suggest adding or removing English punctuation (commas, periods, quotation marks).
   - All spacing is handled by a separate pipeline.

4. TARGETED REPLACEMENTS (DIFFS ONLY):
   - You MUST NOT return the full ayah.
   - You MUST output only the exact erroneous phrase (`target_phrase`) and the concise corrected phrase (`replacement_phrase`).
   - `target_phrase` MUST be an exact substring present inside the provided Thai text.
   - NEVER remove or modify parenthetical tafsir notes `(...)` unless the note itself contains an error.

=== OUTPUT SCHEMA (STRICT JSON ONLY) ===
Return a JSON array of findings:
[
  {
    "ayah": 1,
    "issue_type": "TYPO | MISTRANSLATION | OMISSION | THEOLOGICAL",
    "target_phrase": "exact erroneous substring in current Thai text",
    "replacement_phrase": "precise corrected Thai substring",
    "reason_explanation": "concise scholarly explanation citing the Arabic word and reason"
  }
]
If no issues are found, return `[]`.
"""

def create_audit_prompt(surah_num: int, batch: List[Dict[str, Any]]) -> str:
    entries = []
    for v in batch:
        entries.append(
            f"--- AYAH {v['ayah']} ---\n"
            f"[Arabic Uthmani]: {v['arabic']}\n"
            f"[Malay Basmeih ]: {v['malay']}\n"
            f"[Thai v3 Master]: {v['thai']}"
        )
    text_block = "\n\n".join(entries)

    return f"""Audit the following {len(batch)} verses from Surah #{surah_num}.
Remember: Silence on perfection (return `[]` if no clear error). Only report concrete mistranslations, dropped Arabic clauses, or Thai typos. DO NOT touch spacing.

{text_block}

=== REQUIRED JSON OUTPUT SCHEMA ===
[
  {{
    "ayah": 1,
    "issue_type": "TYPO",
    "target_phrase": "misspelled_text",
    "replacement_phrase": "corrected_text",
    "reason_explanation": "explanation..."
  }}
]
"""


# ---------------------------------------------------------------------------
# API Execution with Smart Fallback
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
                    if "findings" in parsed and isinstance(parsed["findings"], list):
                        return parsed["findings"], model_name, key_id
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

    raise RuntimeError(f"Failed to get valid audit response after trying all models and keys.")


# ---------------------------------------------------------------------------
# Dynamic Character-Budget Batcher
# ---------------------------------------------------------------------------
def create_dynamic_batches(ayahs: List[Dict[str, Any]], char_budget: int = DEFAULT_CHAR_BUDGET) -> List[List[Dict[str, Any]]]:
    batches = []
    current_batch = []
    current_chars = 0

    for a in ayahs:
        a_len = len(a.get("thai", "")) + len(a.get("arabic", "")) + len(a.get("malay", ""))
        if current_batch and (current_chars + a_len > char_budget):
            batches.append(current_batch)
            current_batch = [a]
            current_chars = a_len
        else:
            current_batch.append(a)
            current_chars += a_len

    if current_batch:
        batches.append(current_batch)
    return batches


# ---------------------------------------------------------------------------
# Deterministic Invariant Safety Guardrail Layer
# ---------------------------------------------------------------------------
def apply_safety_guardrails(original_thai: str, target_phrase: str, replacement_phrase: str, issue_type: str) -> Tuple[bool, str, str]:
    """
    Validates that a proposed diff does not violate mathematical text integrity.
    """
    # 0. Reject pure whitespace differences (Decoupled to Pipeline 2)
    if ''.join(target_phrase.split()) == ''.join(replacement_phrase.split()):
        return False, original_thai, "REJECTED_PURE_SPACING (Handled exclusively by Pipeline 2)"

    # 1. Exact Substring Match Check
    if target_phrase not in original_thai:
        return False, original_thai, f"Target phrase '{target_phrase}' was not found verbatim in master Thai verse."

    new_thai = original_thai.replace(target_phrase, replacement_phrase, 1)

    # 2. Parenthetical Tafsir Lock Invariant
    orig_brackets = set(re.findall(r'\([^)]*\)', original_thai))
    new_brackets = set(re.findall(r'\([^)]*\)', new_thai))
    stripped_brackets = orig_brackets - new_brackets
    if stripped_brackets:
        return False, original_thai, f"Unauthorized deletion of parenthetical tafsir note: {stripped_brackets}"

    # 3. Length Delta Guardrail
    delta = len(new_thai) - len(original_thai)
    if issue_type == "TYPO" and abs(delta) > 15:
        return False, original_thai, f"Typo fix altered length by {delta} characters (expected <= 15 chars)."
    if issue_type == "MISTRANSLATION" and delta < -50:
        return False, original_thai, f"Mistranslation fix shrank text by {abs(delta)} characters (potential clause drop)."

    return True, new_thai, "PASSED_GUARDRAIL"


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


def export_findings_csv(checkpoint: Dict[str, Any], master_data: List[Dict[str, Any]]):
    master_lookup = {f"{v['surah']}:{v['ayah']}": v for v in master_data}
    findings = []

    for key, data in checkpoint.items():
        if data.get("is_audited") and data.get("findings"):
            s_num, a_num = map(int, key.split(":"))
            master_entry = master_lookup.get(key, {})
            for item in data["findings"]:
                findings.append({
                    "surah": s_num,
                    "ayah": a_num,
                    "issue_type": item.get("issue_type", "UNKNOWN"),
                    "explanation": item.get("reason_explanation", ""),
                    "target_phrase": item.get("target_phrase", ""),
                    "replacement_phrase": item.get("replacement_phrase", ""),
                    "guardrail_status": item.get("guardrail_status", ""),
                    "original_thai": master_entry.get("thai", ""),
                    "proposed_thai": item.get("proposed_thai", master_entry.get("thai", "")),
                    "arabic_anchor": item.get("arabic_anchor", ""),
                    "malay_anchor": item.get("malay_anchor", ""),
                    "malay_reference": master_entry.get("malay", ""),
                    "arabic_text": master_entry.get("arabic", ""),
                    "reviewer_decision": ""
                })

    findings.sort(key=lambda x: (x["surah"], x["ayah"]))

    with open(OUTPUT_REPORT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "surah", "ayah", "issue_type", "explanation", "target_phrase", "replacement_phrase",
            "guardrail_status", "original_thai", "proposed_thai", "arabic_anchor", "malay_anchor",
            "malay_reference", "arabic_text", "reviewer_decision"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(findings)

    with open(OUTPUT_REVIEW_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(findings)


# ---------------------------------------------------------------------------
# Main Audit Controller
# ---------------------------------------------------------------------------
def run_scholar_audit(surah_range: Optional[List[int]] = None, char_budget: int = DEFAULT_CHAR_BUDGET):
    print("\n" + "="*70)
    print("PIPELINE 1: SCHOLAR AUDITOR v4 (THEOLOGICAL & TYPO ENGINE)")
    print("="*70)

    if not os.path.exists(MASTER_DATA_FILE):
        raise FileNotFoundError(f"Master file not found: {MASTER_DATA_FILE}")
    with open(MASTER_DATA_FILE, "r", encoding="utf-8") as f:
        master_data: List[Dict[str, Any]] = json.load(f)
    print(f"Loaded {len(master_data)} aligned verses from master dataset.")

    env_file = os.path.join(SCRIPT_DIR, ".env")
    pool = MultiKeyClientPool(env_file)

    surahs: Dict[int, List[Dict[str, Any]]] = {}
    for entry in master_data:
        s = entry["surah"]
        if surah_range and s not in surah_range:
            continue
        surahs.setdefault(s, []).append(entry)

    checkpoint = load_checkpoint()
    total_audited_initial = sum(1 for k, v in checkpoint.items() if v.get("is_audited"))
    print(f"Surahs in scope: {len(surahs)} | Already cached in checkpoint: {total_audited_initial} ayahs")

    total_ayahs_in_scope = sum(len(v) for v in surahs.values())
    total_flagged_count = 0

    for s_num, ayahs in surahs.items():
        needed_ayahs = [a for a in ayahs if not checkpoint.get(f"{s_num}:{a['ayah']}", {}).get("is_audited")]
        if not needed_ayahs:
            print(f"Surah {s_num:3d} already fully audited. Skipping.", flush=True)
            continue

        batches = create_dynamic_batches(needed_ayahs, char_budget=char_budget)
        print(f"\n--> Auditing Surah {s_num:3d} ({len(needed_ayahs)} remaining ayahs in {len(batches)} dynamic micro-batches)...", flush=True)

        for b_idx, batch in enumerate(batches, 1):
            ayah_range_str = f"{batch[0]['ayah']}-{batch[-1]['ayah']}" if len(batch) > 1 else f"{batch[0]['ayah']}"
            prompt = create_audit_prompt(s_num, batch)

            try:
                results, used_model, key_id = call_genai_with_fallbacks(pool, prompt)
            except Exception as e:
                print(f"    CRITICAL FAILURE on Surah {s_num} Ayahs {ayah_range_str}: {e}", flush=True)
                continue

            findings_by_ayah: Dict[int, List[Dict[str, Any]]] = {}
            for item in results:
                a_num = item.get("ayah")
                if a_num:
                    findings_by_ayah.setdefault(a_num, []).append(item)

            for v in batch:
                a_num = v["ayah"]
                key = f"{s_num}:{a_num}"
                orig_text = v["thai"]
                v_findings = findings_by_ayah.get(a_num, [])

                processed_findings = []
                for f_item in v_findings:
                    target_p = f_item.get("target_phrase", "")
                    repl_p = f_item.get("replacement_phrase", "")
                    i_type = f_item.get("issue_type", "TYPO")

                    is_valid, new_text, g_status = apply_safety_guardrails(orig_text, target_p, repl_p, i_type)
                    if g_status != "REJECTED_PURE_SPACING (Handled exclusively by Pipeline 2)":
                        f_item["guardrail_status"] = g_status
                        f_item["proposed_thai"] = new_text if is_valid else orig_text
                        processed_findings.append(f_item)
                        total_flagged_count += 1

                checkpoint[key] = {
                    "is_audited": True,
                    "model": used_model,
                    "findings": processed_findings,
                    "timestamp": time.time()
                }

            save_checkpoint(checkpoint)
            total_now = sum(1 for k, v in checkpoint.items() if v.get("is_audited"))
            flag_notice = f" [! {len(processed_findings)} issue(s) flagged]" if processed_findings else " [Clean]"
            print(f"    [{used_model} Key #{key_id}] Surah {s_num} Ayahs {ayah_range_str} ({len(batch)} ayahs) audited.{flag_notice} ({total_now}/{total_ayahs_in_scope} total)", flush=True)

        export_findings_csv(checkpoint, master_data)

    print("\n" + "="*70)
    print("Pipeline 1: Scholar Audit v4 Complete!")
    print(f"Total Ayahs Audited: {sum(1 for k, v in checkpoint.items() if v.get('is_audited'))}")
    print(f"Total Flags for Human Review: {total_flagged_count}")
    print(f"1. Audit Findings CSV: {OUTPUT_REPORT_CSV}")
    print(f"2. Human Review Sheet: {OUTPUT_REVIEW_CSV}")
    print("="*70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline 1: Scholar Auditor v4 - Tri-Lingual Quran Translation Auditor")
    parser.add_argument("--surahs", type=str, default="all", help="Surah range e.g. 'all', '1-10', '114', or '1,2,3'")
    parser.add_argument("--char_budget", type=int, default=DEFAULT_CHAR_BUDGET, help="Max characters per dynamic prompt payload (default: 1000)")
    parser.add_argument("--reset_checkpoint", action="store_true", help="Reset checkpoint and re-audit from scratch")

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

    run_scholar_audit(surah_range=surah_range, char_budget=args.char_budget)
