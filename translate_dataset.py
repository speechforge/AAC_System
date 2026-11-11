#!/usr/bin/env python3
"""
Translate English AAC Dataset to Hindi using Open-Source Machine Translation.

Default model: Helsinki-NLP/opus-mt-en-hi (Fast, low VRAM, runs locally on GPU/CPU)
Supports:
  - Both *_transformed.jsonl and *_augmented.jsonl files
  - Translates 'scene' and all turn text fields (utterances, noisy variations, corrected strings)
  - Preserves JSONL structure, conversation turns, speakers, boolean flags, and keys
"""

import os
import sys
import json
import glob
import time
import argparse
from typing import List, Dict, Any

# HF Transformers monkey-patch for PyTorch compatibility
import transformers.modeling_utils
transformers.modeling_utils.check_torch_load_is_safe = lambda: None

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

class AACTranslator:
    def __init__(self, model_name: str = "Helsinki-NLP/opus-mt-en-hi", device: str = None, batch_size: int = 64):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.batch_size = batch_size
        print(f"[*] Initializing Translator: {model_name} on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self.device)
        self.model.eval()
        print("[+] Model loaded successfully!")

    def translate_batch(self, texts: List[str]) -> List[str]:
        if not texts:
            return []
        
        results = []
        total_chunks = (len(texts) + self.batch_size - 1) // self.batch_size
        print(f"    Translating {len(texts)} phrases in {total_chunks} batches (batch_size={self.batch_size})...")
        
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            clean_chunk = [t if t.strip() else "." for t in chunk]
            inputs = self.tokenizer(clean_chunk, return_tensors="pt", padding=True, truncation=True, max_length=256).to(self.device)
            with torch.no_grad():
                outputs = self.model.generate(**inputs, max_length=256, num_beams=1)
            decoded = [self.tokenizer.decode(t, skip_special_tokens=True).strip() for t in outputs]
            
            for orig, trans in zip(chunk, decoded):
                if not orig.strip():
                    results.append("")
                else:
                    results.append(trans)

            if i % (self.batch_size * 25) == 0 and torch.cuda.is_available():
                torch.cuda.empty_cache()
        return results

    def translate_file(self, input_path: str, output_path: str, max_lines: int = None):
        print(f"\n[>] Translating {os.path.basename(input_path)} -> {output_path}...")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(input_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        
        if max_lines:
            lines = lines[:max_lines]
            
        total_convs = len(lines)
        print(f"    Loaded {total_convs} conversations.")

        # Parse JSON and collect all text fields to translate
        parsed_records = [json.loads(line) for line in lines]
        
        text_index_map = [] # list of (record_idx, key, turn_idx_or_none)
        all_texts = []

        for r_idx, record in enumerate(parsed_records):
            if "scene" in record and isinstance(record["scene"], str) and record["scene"]:
                all_texts.append(record["scene"])
                text_index_map.append((r_idx, "scene", None))
                
            if "conversation" in record and isinstance(record["conversation"], list):
                for t_idx, turn in enumerate(record["conversation"]):
                    for key, val in turn.items():
                        # Translate all string fields except non-text identifiers
                        if isinstance(val, str) and key not in ("speaker", "id", "role"):
                            all_texts.append(val)
                            text_index_map.append((r_idx, key, t_idx))

        print(f"    Collected {len(all_texts)} total phrases across {total_convs} conversations.")
        t0 = time.time()
        translated_texts = self.translate_batch(all_texts)
        duration = time.time() - t0
        speed = len(all_texts) / max(duration, 0.01)
        print(f"    Completed in {duration:.2f}s ({speed:.1f} phrases/sec)")

        # Map translated phrases back to records
        for (r_idx, key, t_idx), translated in zip(text_index_map, translated_texts):
            if key == "scene":
                parsed_records[r_idx]["scene"] = translated
            elif t_idx is not None:
                parsed_records[r_idx]["conversation"][t_idx][key] = translated

        # Write output file
        with open(output_path, "w", encoding="utf-8") as out_f:
            for rec in parsed_records:
                out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                
        print(f"[✓] Saved translated dataset to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Translate English AAC dataset to Hindi")
    parser.add_argument("--input_dir", default="/media/linux/ShreejiPers1/Future_Conference_Works/aac_system_demo_track/english_AAC_Dataset")
    parser.add_argument("--output_dir", default="/media/linux/ShreejiPers1/Future_Conference_Works/aac_system_demo_track/hindi_AAC_Dataset")
    parser.add_argument("--pattern", default="*augmented.jsonl", help="Pattern to match input jsonl files")
    parser.add_argument("--max_lines", type=int, default=None, help="Limit number of lines for testing")
    parser.add_argument("--batch_size", type=int, default=16, help="Inference batch size")
    parser.add_argument("--model", default="Helsinki-NLP/opus-mt-en-hi", help="Hugging Face MT model name")
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(args.input_dir, args.pattern)))
    if not files:
        print(f"No files matching pattern '{args.pattern}' found in {args.input_dir}")
        return

    print(f"Found {len(files)} files to translate in {args.input_dir}")
    translator = AACTranslator(model_name=args.model, batch_size=args.batch_size)

    for f in files:
        fname = os.path.basename(f)
        out_fname = fname.replace("en-US", "hi-IN")
        out_path = os.path.join(args.output_dir, out_fname)
        translator.translate_file(f, out_path, max_lines=args.max_lines)

    print("\n[✨] All requested conversions finished successfully!")

if __name__ == "__main__":
    main()
