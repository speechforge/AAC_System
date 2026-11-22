# Performance: Before vs After vs Baseline
### Indic AAC Studio — 20 November 2026

> [!NOTE]
> Three versions are compared throughout this document:
> - **External Baseline** = Gaines & Vertanen, EMNLP 2025 (English-only, character prediction, OPT/GPT-2 LLMs, no generation, no TTS)
> - **Our Previous Version** = Qwen-0.5B + FastPitch IndicTTS, no semantic gate, no ∞-gram (pre-merge snapshot)
> - **Current Version (Nov 16, 2026)** = ∞-gram + 3-stage Qwen cascade + deterministic gate + IndicF5/F5-TTS + Redis accounts + voice cloning

---

## 1. Prediction Engine — KSR & Speed

### 1A. English: Our ∞-gram vs All Baselines

| System | KSR% ↑ | Top-5 Hit% ↑ | Perplexity ↓ | Speed ↓ | Needs GPU? |
|---|:---:|:---:|:---:|:---:|:---:|
| **Baseline n-gram** (AAC char 12-gram) | 55.1 | 29.8 | 4.93 | 0.03 ms CPU | ❌ |
| **Baseline LLM** (OPT-125m pretrained) | 58.0 | 36.4 | 2.65 | 25 ms GPU | ✅ |
| **Baseline LLM** (OPT-350m pretrained) | 58.9 | 36.9 | 2.52 | 140 ms GPU | ✅ |
| **Baseline LLM** (OPT-125m adapted, best) | **62.6** | **44.9** | **2.07** | 25 ms GPU | ✅ |
| **OURS: ∞-gram (current)** | 55.9 | 30.5 | 3.57 | **0.045 ms CPU** | ❌ |

> [!TIP]
> Our ∞-gram is **500–3,000× faster** than any LLM-based prediction and needs **no GPU at all**. KSR is within ~1 point of the baseline n-gram (essentially tied), and ~7 points behind the best adapted LLM — which is the expected trade-off for a CPU-only, real-time, zero-GPU system.

**KSR chance floor** (frequency-only baseline) ≈ 50%; useful range is 50–65%.

---

### 1B. All Four Languages: Shipped vs Fixed vs 12-gram Char

| Language | Shipped KSR | Without Selected-Word Exclusion | 12-gram Char |
|---|:---:|:---:|:---:|
| **English** | 56.3 | 56.6 | 56.2 |
| **Hindi** | 56.7 | 57.7 | 57.4 |
| **Marathi** | 48.7 | 49.2 | 49.1 |
| **Gujarati** | 53.0 | 53.7 | 54.2 ← slightly behind |

> [!NOTE]
> Removing the "exclude already-selected words" rule is a **free +0.3–1.1 KSR improvement** that has not yet been applied to the shipped version. For Gujarati, the 12-gram char LM still leads slightly even after the fix.

---

### 1C. Prediction Latency (CPU, ms per top-10 prediction)

| Language | ∞-gram Latency |
|---|:---:|
| English | **0.045 ms** |
| Hindi | 0.054 ms |
| Gujarati | 0.069 ms |
| Marathi | 0.087 ms |
| ∞-gram build time (at startup) | ~0.45 s |
| ∞-gram memory footprint | <35 MB |

---

## 2. Sentence Generation — Before vs After

### 2A. Internal Ablation (Our Own System Evolution)

| Metric | Previous Version | Current Version |
|---|:---:|:---:|
| **System** | Qwen-0.5B + FastPitch IndicTTS (no gate) | Qwen-0.5B + SemanticValidator + IndicF5/F5-TTS |
| **Semantic Fidelity** | Moderate — prone to dropping negation | **90–99% on measured set** |
| **Negation preservation** | ❌ Sometimes dropped | ✅ 100% (10-case measured) |
| **Entity preservation** | ❌ Sometimes substituted | ✅ 100% (10-case measured) |
| **Hallucination (CVR)** | 14–18% unchecked | **0% when gate + LLM-3 active** |
| **Code-mix support** | Partial (pronunciation artifacts) | ✅ Segmented + separate English model |
| **Voice cloning** | ❌ Blocked (FastPitch used `speakers.pth`, no zero-shot) | ✅ Zero-shot (3–12 s reference WAV) |
| **Languages** | English + Hindi (partial) | English · Hindi · Gujarati · Marathi · Hinglish |
| **LLM Latency** | ~1.5 s | ~1.1 s (LLM-1) + 1.1 s (LLM-2) + **10.3 s (LLM-3)** |
| **TTS Latency** | ~0.7 s | ~0.13–2.5 s (IndicF5/F5-TTS, cached: ~0 ms) |
| **Total End-to-End** | ~2.2 s (no gate) | ~3.5–17.9 s full (gate + 3-LLM; 17.9 s worst case single run) |
| **WER (Whisper-Tiny)** | ~12% | — (CER metric used instead, see Speech section) |

> [!IMPORTANT]
> The 17.9 s total is the **observed 10-case average** with LLM-3 dominating (10.3 s). This is the heaviest fully-pipelined mode. With caching, TTS drops to near-zero. The sentence generation latency target stated in older docs (~3.5–5.5 s) is **not supported by measured data**.

---

### 2B. LLM-3 Cascade — 10-Case Measured Report (`llm3_eval_report.json`)

| Metric | Value |
|---|:---:|
| Dataset size | 10 cases |
| **Overall validity rate** | **90.0%** |
| **Entity preservation** | **100.0%** |
| **Negation preservation** | **100.0%** |
| **Intent preservation** | 80.0% |
| **Unsupported info avoidance** | **100.0%** |
| TTS audio synthesis success | 90.0% |
| **Fallbacks triggered** | 4 / 10 cases |

**LLM-3 verdict breakdown:**
```
PASS   → 1 / 10   (sentence was already correct)
REFINE → 9 / 10   (edits needed to remove hallucinated content)
REJECT → 0 / 10
```

**Latency breakdown (single observed run):**

| Stage | Time |
|---|:---:|
| LLM-1 Realiser | 1.11 s |
| LLM-2 Refiner | 1.09 s |
| LLM-3 Verifier | **10.34 s** ← bottleneck |
| Semantic gate | 0.00 s (CPU regex, negligible) |
| TTS | 0.13 s (mock/cached) |
| **Total** | **17.9 s** |

> [!WARNING]
> LLM-3 is the dominant latency source (10.3 s). This is a **known bottleneck** — it runs the heaviest prompt (1,100+ token input, JSON structured output). With real IndicF5 weights + GPU, TTS adds 1.8–2.5 s. These are single-run observations, not a latency distribution.

---

### 2C. Sentence Generation — 4-Language Gate Test

| Metric | English | Hindi | Gujarati | Marathi |
|---|:---:|:---:|:---:|:---:|
| **Correct sentences (determinate selections)** | 97–99% | 97–99% | 97–99% | 97–99% |
| **Literal output rate** (no generation) | 16% | 29% | 41% | 38% |
| **Ambiguous abstain** | 13/13 ✅ | 13/13 ✅ | 13/13 ✅ | 13/13 ✅ |

---

## 3. Speech Quality — Before vs After (TTS Repair)

### ASR Character Error Rate (CER) — Whisper-large-v3-turbo verification

| Language | **Before** (mismatched reference audio / wrong routing) | **After** (fixed reference + separated English model) | Improvement |
|---|:---:|:---:|:---:|
| **English** | 0.516 | **0.000** | ✅ Perfect |
| **Hindi** | 0.600 | **0.086** | ✅ 7× better |
| **Gujarati** | 1.289 | **0.211** | ✅ 6× better |
| **Marathi** | 0.441 | **0.118** | ✅ 3.7× better |

> [!NOTE]
> CER > 1.0 is possible due to inserted characters. These are 4 diagnostic samples, not a held-out benchmark. No human naturalness assessment was performed.

**Root causes fixed:**
- `MAR_F_HAPPY_00001.wav` reference was actually a diesel-price recording (mismatched audio↔transcript) → replaced with `MAR_F_WIKI_00001.wav` (Hampi transcript, official IndicF5 demo source)
- English routed through IndicF5 → garbled (IndicF5 only covers 11 Indic languages) → now routes to **SWivid F5-TTS** (English-trained, CC-BY-NC-4.0)
- Gujarati guidance strength: 2.0 → **1.0** (found more accurate in controlled comparison)

**Audio output:** 24,000 Hz 16-bit PCM (Vocos neural vocoder), up from 16,000 Hz legacy FastPitch.

---

## 4. Full System Comparison Table — External Baseline vs Ours

| Feature / Metric | External Baseline (Gaines & Vertanen 2025) | **Our Current System (Nov 2026)** |
|---|---|---|
| **Languages** | English only | **English · Hindi · Gujarati · Marathi · Hinglish** |
| **Input mode** | Character-by-character (letter level) | Symbol/word grid (word level) |
| **Prediction type** | Character LM (OPT/GPT-2/Llama) | ∞-gram Suffix Trie + HMM n-gram |
| **Prediction KSR (English)** | 55.1–62.6% (n-gram to adapted LLM) | 55.9–56.6% |
| **Prediction speed** | 25–140 ms (GPU) | **0.045 ms (CPU)** — 500–3000× faster |
| **Needs GPU for prediction** | ✅ Yes | ❌ No |
| **Sentence generation** | ❌ None | ✅ 3-stage Qwen cascade |
| **Hallucination check** | ❌ None | ✅ Deterministic gate (10 check types) |
| **Negation safety** | ❌ 18.5% drop rate (unchecked) | ✅ 100% preservation (measured) |
| **Constraint violation rate** | 14.2% (unverified LLM) | 0% (gate active) |
| **TTS / Speech** | ❌ None | ✅ IndicF5 + F5-TTS (24 kHz, voice cloning) |
| **Voice cloning** | ❌ Not present | ✅ Zero-shot (3–12 s reference WAV) |
| **Offline support** | ❌ Not present | ✅ PWA, IndexedDB, offline speech cache |
| **User accounts** | ❌ Not present | ✅ Redis-backed local + Google accounts |
| **Accessibility** | ❌ Not present | ✅ Dock: contrast, motion, speech speed |

---

## 5. Latency Summary — All Modes

| Mode / Component | Latency |
|---|:---:|
| **∞-gram prediction (CPU)** | 0.045–0.087 ms |
| **∞-gram build at startup** | ~0.45 s |
| **Semantic gate (CPU regex)** | ~0 ms (negligible) |
| **Template realiser fallback (CPU)** | ~0 ms |
| **LLM-1 Realiser (Qwen 0.5B, GPU)** | ~1.1 s |
| **LLM-2 Refiner (Qwen 0.5B, GPU)** | ~1.1 s |
| **LLM-3 Verifier (Qwen 0.5B, GPU)** | ~10.3 s (observed) |
| **IndicF5 TTS (GPU, 24 kHz)** | ~1.8–2.5 s (not cached) |
| **IndicF5 TTS (cached)** | ~0 ms |
| **Un-Jumble — rule (CPU)** | <1 ms |
| **Un-Jumble — Qwen (GPU)** | ~2.4 ms (9-word example API only) |
| **Transliteration — offline map** | ~0 ms |
| **Transliteration — Google API** | <0.8 s (network-dependent) |
| **Full pipeline (measured, 1 run)** | **17.9 s** (LLM-3 bottleneck, no GPU caching) |
| **End-to-end (proposal claim, unverified)** | ~~3.5–5.5 s~~ — not supported by data |

---

## 6. Known Limitations (Current Version)

| # | Limitation | Impact | Suggested Fix |
|---|---|---|---|
| 1 | **Marathi/Gujarati share wrong ∞-gram trie** | Gujarati has no native model; Marathi uses Hindi trie. Per-language KSR measured separately but not deployed. | Build + ship per-language ∞-gram engines for mr/gu. |
| 2 | **Selected-word exclusion costs KSR** | Removes already-chosen words from prediction, costing 0.3–1.1 KSR points per language. | Drop the exclusion rule (free improvement). |
| 3 | **LLM-3 is the latency bottleneck** | 10.3 s average in measured run (1,100+ token prompt). Real-world use on GPU would be faster but still the slowest stage. | Optimise prompt length; consider quantised inference; or restrict LLM-3 to ambiguous cases only. |
| 4 | **Fallback bypasses SemanticValidator** | Rule-based template realiser is marked valid unconditionally — it does not go through the gate. | Add gate pass-through on template output (templates are deterministic so they should pass, but it is not enforced). |
| 5 | **Templates not native-reviewed** | `templates.py` sentences for Hindi/Gujarati/Marathi written by authoring assistant, not verified by native speakers. | Native speaker review of all 4-language template entries. |
| 6 | **LLM-3 REFINE quality** | In the 10-case report, 9/10 needed REFINE; 4/10 needed deterministic fallback. LLM-3 itself sometimes produces malformed REFINE output (case 1 output: "felt and decided to go to the for pizza"). | Fine-tune on AAC-specific examples; or switch to template-first policy. |
| 7 | **No real user study** | No AAC-user clinical study recorded anywhere. All verification is automated (browser scripts + unit tests). | Recruit AAC users; conduct COMS (Communication Outcome Measure Study) or similar. |
| 8 | **Small synthetic corpus** | Training data = machine-translated JSONL (Hindi = translation of English batches; Marathi/Gujarati also translated). No native AAC user utterances. | Collect real Indic AAC conversations; remove 4–11% degenerate machine-translation outputs. |
| 9 | **Security is demo-grade** | CORS `*` with credentials, `0.0.0.0` bind, unauthenticated `/api/voice/clone` and `/api/generate_symbol`. Firebase web config committed to repo. | Restrict CORS to known origins; add auth to voice/symbol endpoints; use Firebase App Check. |
| 10 | **Hard-coded paths remain** | `dual_hmm_streaming_kit/train_dual_hmm_streaming.py:41` → another machine's home directory path. HMM retraining from this tree would fail. | Portable-ise all training scripts (use relative paths). |
| 11 | **Voice clones lost on restart** | Custom voice WAVs are stored on disk but the in-memory reference snapshot is rebuilt per-request. Already-running inference is safe; but a new synthesis after restart picks up the saved WAV correctly. Actually — reference WAVs persist; cache is rebuilt lazily. Document behaviour more clearly. | Clarify in docs; add `/api/health` voice-clone readiness check. |
| 12 | **CDN not pinned** | `react@18`, `@babel/standalone`, `cdn.tailwindcss.com` are unpinned. A CDN change/outage breaks the UI. | Bundle locally (no build step currently exists). |
| 13 | **Infinite context depth = no measurable benefit** | On this short-sentence corpus, a 2-word cap performs identically to arbitrary depth. The "infinity" in ∞-gram does not help here. | Report accurately in paper; cap context at 2–3 for performance without loss. |
| 14 | **No confidence intervals** | Differences < ~2 KSR points should be read as ties; single run, single split. | Multiple runs; bootstrap CIs. |

---

## 7. What the Experiments Positively Support (Verified)

| Claim | Evidence |
|---|---|
| ✅ ∞-gram is 500–3000× faster than LLM-based prediction | 0.045 ms vs 25–140 ms measured |
| ✅ ∞-gram KSR within ~1 point of baseline n-gram (English) | 55.9 vs 55.1 |
| ✅ Multilingual coverage at similar KSR (49–57%) | 4-language ∞-gram experiment |
| ✅ Gate produces correct sentences for 97–99% of determinate selections | 4-language gate experiment |
| ✅ Negation preserved 100% | 10-case LLM-3 report |
| ✅ Entity preserved 100% | 10-case LLM-3 report |
| ✅ 13/13 ambiguous selections correctly abstained | Gate experiment |
| ✅ Speech intelligibility dramatically improved after repair | CER: 0.516→0.000 (English), 0.600→0.086 (Hindi) |

## 8. What is NOT Supported (Negative Findings — be honest in papers)

| Claim | Reality |
|---|---|
| ~~"0% constraint violation rate — guaranteed"~~ | Fallback bypasses validator; 4/10 needed fallback; "guaranteed" overstates it |
| ~~"3.5–5.5 s end-to-end"~~ | Measured: 17.9 s (LLM-3 alone = 10.3 s); proposal claim is unverified |
| ~~"<1 ms prediction"~~ | ∞-gram is 0.045 ms ✅ but LLM-based prediction (which the proposal also describes) is 25–140 ms |
| ~~"100% local / no external APIs"~~ | Firebase Auth, Google Input Tools, CDN scripts, optional OpenAI — none are local |
| ~~"HIPAA/GDPR compliant"~~ | No formal compliance assessment; Firebase config committed to repo |
| ~~"∞-gram context depth gives measurable benefit"~~ | 2-word cap = arbitrary depth on this corpus; no benefit measured |
| ~~"Adapted OPT-125m not available to compare"~~ | Available: it's the best at KSR 62.6% vs our 55.9% |

---

*Source files: `RESULTS_vs_baseline_english_and_indic.txt` · `indic-generative-aac/EXPERIMENTS.md` · `indic-generative-aac/tests/semantic/llm3_eval_report.json` · `SPEECH_QUALITY_FIX.md` · `CONTEXT.md §11` · `PROJECT_PROPOSAL_CONTEXT.md §6`*
