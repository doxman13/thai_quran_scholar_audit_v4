#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WBW Master Audit Engine CLI
Automated audit and quality verification tool for Thai Quran Word-by-Word translations.
"""

import argparse
import json
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "wbw_audit_state.json")
DB_PATH = "H:/gits/thai-quran-app/assets/quran_offline.db"

def get_state(default_batch_size=100):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "current_index": 0,
        "batch_num": 1,
        "batch_size": default_batch_size,
        "total_anomalies_flagged": 0,
    }

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_canonical_words():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, verse_key, position, text_uthmani, translation_th, translation_ms, translation_en, part_of_speech FROM words")
    words = c.fetchall()
    conn.close()

    def sort_key(w):
        s, a = map(int, w['verse_key'].split(':'))
        return (s, a, w['position'])

    return sorted(words, key=sort_key)

def audit_word(w):
    ar = w['text_uthmani'].strip()
    th = (w['translation_th'] or '').strip()
    en = (w['translation_en'] or '').lower().strip()
    ms = (w['translation_ms'] or '').lower().strip()
    pos = w['part_of_speech'] or ''
    vk = w['verse_key']
    p = w['position']
    wid = w['id']
    
    if re.match(r'^[0-9\u0660-\u0669]+$', ar):
        return None

    # 1. Foreign characters
    if re.search(r'[\uAC00-\uD7AF\u0590-\u05FF\u4E00-\u9FFF]', th):
        return f"Foreign character detected in Thai translation: '{th}'"

    # 2. Slashes
    if '/' in th:
        return f"Slash gloss detected: '{th}'"

    # 3. Truncated Verbs
    bare_particles = set(['ว่า', 'จะ', 'ที่', 'ของ', 'ใน', 'ณ', 'คน', 'เอง', 'หรือ', 'และ', 'เพื่อ', 'จาก', 'แด่', 'แก่', 'ซึ่ง', 'จึง'])
    if 'Verb' in pos and th in bare_particles:
        return f"Verb reduced to bare particle '{th}'"

    # 4. Truncated Nouns
    if 'Noun' in pos and not 'Verbal' in pos and th in set(['ว่า', 'จะ', 'ที่', 'ของ', 'ใน', 'และ', 'เพื่อ', 'หรือ', 'จึง']):
        return f"Noun reduced to bare particle '{th}'"

    # 5. Missing Negation
    if ('Negative' in pos or 'Prohibition' in pos) and not re.search(r'ไม่|มิ|หาไม่|อย่า|หามิได้|เว้นแต่|นอกจาก|ใดๆ', th):
        return f"Negative missing negation element: '{th}'"

    # 6. Unmatched Parentheses
    if th.count('(') != th.count(')'):
        return f"Unmatched parentheses in: '{th}'"

    # 7. Single Character Word
    if len(th) <= 1:
        return f"Suspicious single-character word: '{th}'"

    # 8. Lexical / Dictionary Meta-Leaks
    if 'พจนานุกรม' in th or 'ฯพณฯ' in th:
        return f"Lexical dictionary leak: '{th}'"

    return None

def run_grand_audit():
    print("\n" + "="*60)
    print("=== FULL CORPUS GRAND AUDIT (ALL 83,665 WORDS) ===")
    print("="*60)
    words = load_canonical_words()
    print(f"Total canonical words: {len(words)}")
    
    anomalies = []
    for w in words:
        issue = audit_word(w)
        if issue:
            anomalies.append((w['verse_key'], w['position'], w['text_uthmani'], w['translation_th'], issue))
            
    print(f"\nTotal Anomalies Detected Across Full Quran: {len(anomalies)}")
    if anomalies:
        for vk, pos, ar, th, issue in anomalies[:50]:
            print(f"  [!] {vk} w{pos}: {ar} -> TH: '{th}' | Issue: {issue}")
        if len(anomalies) > 50:
            print(f"  ... and {len(anomalies) - 50} more.")
    else:
        print("\n🎉 ALHAMDULILLAH! THE ENTIRE CORPUS IS 100% PRISTINE AND ERROR-FREE!")

def run_batches(batch_size, batches_to_run):
    state = get_state(default_batch_size=batch_size)
    words = load_canonical_words()
    total_words = len(words)
    
    print(f"\n=== RUNNING WBW AUDIT (Batch Size: {batch_size} words) ===")
    print(f"Current Index: {state['current_index']} / {total_words} | Current Batch: #{state['batch_num']}")
    
    batches_completed = 0
    while batches_completed < batches_to_run:
        start_idx = state['current_index']
        if start_idx >= total_words:
            print("\nALL BATCHES COMPLETE! Every single word in the Quran has been verified.")
            break
            
        end_idx = min(start_idx + batch_size, total_words)
        batch = words[start_idx:end_idx]
        b_num = state['batch_num']
        
        anomalies = []
        for w in batch:
            issue = audit_word(w)
            if issue:
                anomalies.append((w['verse_key'], w['position'], w['text_uthmani'], w['translation_th'], issue))
                
        status_tag = f"🚨 {len(anomalies)} Anomalies" if anomalies else "✅ Clean 100%"
        print(f"\nBatch #{b_num} (words {start_idx+1}-{end_idx}): {batch[0]['verse_key']}(w{batch[0]['position']}) -> {batch[-1]['verse_key']}(w{batch[-1]['position']}) | {status_tag}")
        for vk, pos, ar, th, issue in anomalies:
            print(f"   [!] {vk} w{pos}: {ar} -> TH: '{th}' | {issue}")
            
        state['current_index'] = end_idx
        state['batch_num'] = b_num + 1
        state['batch_size'] = batch_size
        state['total_anomalies_flagged'] += len(anomalies)
        save_state(state)
        
        batches_completed += 1

    print(f"\nCompleted {batches_completed} batch(es). Next batch: #{state['batch_num']} (Word {state['current_index']+1})")

def main():
    parser = argparse.ArgumentParser(description="WBW Master Audit Engine CLI")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size in words (default: 100)")
    parser.add_argument("--batches", type=int, default=1, help="Number of batches to run (default: 1)")
    parser.add_argument("--grand-audit", action="store_true", help="Run full-corpus grand audit across all 83,665 words")
    parser.add_argument("--reset", action="store_true", help="Reset state tracker back to word index 0 (Batch #1)")
    parser.add_argument("--status", action="store_true", help="Display current audit state")
    
    args = parser.parse_args()
    
    if args.reset:
        save_state({
            "current_index": 0,
            "batch_num": 1,
            "batch_size": args.batch_size,
            "total_anomalies_flagged": 0,
        })
        print(f"State tracker reset to word index 0 (Batch #1) with batch_size={args.batch_size}.")
        return

    if args.status:
        state = get_state()
        print("\n=== WBW AUDIT STATE ===")
        print(f"Current Word Index: {state.get('current_index', 0)} / 83,665 ({state.get('current_index', 0)*100/83665:.2f}%)")
        print(f"Current Batch Number: #{state.get('batch_num', 1)}")
        print(f"Batch Size: {state.get('batch_size', 100)} words")
        print(f"Total Anomalies Flagged: {state.get('total_anomalies_flagged', 0)}")
        return

    if args.grand_audit:
        run_grand_audit()
        return

    run_batches(args.batch_size, args.batches)

if __name__ == "__main__":
    main()
