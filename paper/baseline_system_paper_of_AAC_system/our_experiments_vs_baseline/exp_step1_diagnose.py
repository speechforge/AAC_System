"""Improvement plan STEP 1 - diagnose the bottleneck before changing models.
A) CPU: data statistics, OOV coverage, oracle KSR ceilings (perfect ranker over our pool / over the whole train vocabulary), gap decomposition.
B) GPU: round-trip (back-translation) audit of the machine-translated Marathi/Gujarati data, with Hindi through the same NLLB model as calibration.
   python exp_step1_diagnose.py cpu | gpu"""
import sys, json, bisect, collections, random, math
from lib import *
mode = sys.argv[1]

def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y: break
        n += 1
    return n

if mode == "cpu":
    out = {}
    for lang in ("en", "hi", "mr", "gu"):
        train = sents(lang, "train"); tests = {"aac": sents(lang, "test", ("aac",)), "care": sents(lang, "test", ("care",))}
        pool = Pool(train, 300); vocab = pool.freq; V = sorted(vocab)
        toks = [w for s in train for w in s.split()]; hap = sum(1 for w, c in vocab.items() if c == 1)
        r = {"train_sentences": len(train), "train_tokens": len(toks), "vocab": len(vocab), "type_token_ratio": len(vocab) / len(toks),
             "hapax_share_of_vocab": hap / len(vocab), "avg_word_len": sum(map(len, toks)) / len(toks), "sets": {}}
        # vocabulary-coverage learning curve (does more data shrink OOV?)
        cur = {}
        for frac in (0.25, 0.5, 1.0):
            sub = train[: int(len(train) * frac)]; vs = set(w for s in sub for w in s.split())
            tw = [w for k in tests for s in tests[k] for w in s.split()]; cur[frac] = 100.0 * sum(w not in vs for w in tw) / len(tw)
        r["oov_token_pct_by_train_fraction"] = cur
        for k, ts in tests.items():
            ws = [w for s in ts for w in s.split()]; oov = [w for w in ws if w not in vocab]
            # near-inflection: OOV word sharing a prefix >=70% of its length with some train word (neighbours in sorted vocab bound the max LCP)
            near = 0
            for w in oov:
                i = bisect.bisect_left(V, w); m = max([lcp(w, V[j]) for j in (i - 1, i) if 0 <= j < len(V)] + [0])
                near += (m >= 0.7 * len(w) and m >= 2)
            # oracle KSR: best possible ranker, same pool (needs w in top-300 prefix matches) / whole train vocabulary (1 key per known word)
            ka = kp_pool = kp_vocab = 0
            for w in ws:
                ka += len(w) + 1; kp_pool_w = len(w) + 1
                for kk in range(len(w)):
                    if w in pool.get(w[:kk]): kp_pool_w = kk + 1; break
                kp_pool += kp_pool_w; kp_vocab += 1 if w in vocab else len(w) + 1
            fin = json.load(open(f"results/final_{lang}.json"))[lang]["systems"]
            cur_k = {n: v[k]["ksr_pct"] for n, v in fin.items()}
            r["sets"][k] = {"words": len(ws), "oov_token_pct": 100.0 * len(oov) / len(ws), "oov_type_pct": 100.0 * len(set(oov)) / len(set(ws)),
                            "oov_near_inflection_pct_of_oov": 100.0 * near / max(len(oov), 1),
                            "oracle_ksr_pool": 100.0 * (ka - kp_pool) / ka, "oracle_ksr_vocab": 100.0 * (ka - kp_vocab) / ka,
                            "shipped_ksr": cur_k["A shipped infinity-gram"], "improved_ksr": cur_k["E step1+5+2+7: + personalisation (recency cache)"]}
        out[lang] = r
        print(lang, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != "sets"}))
        for k, s in r["sets"].items(): print("  ", k, {a: round(b, 1) for a, b in s.items()})
    json.dump(out, open("results/step1_diagnose_cpu.json", "w"), indent=1)
else:
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    random.seed(0)
    en = load("en", "test", "aac") + load("en", "test", "care"); idx = random.sample(range(403), 120)
    # mr/gu files are index-aligned with the English files (403 / 402 sentences)
    srcs, mt = [], {"mr": [], "gu": []}
    for role in ("aac", "care"):
        e = load("en", "test", role)
        for l in mt:
            assert len(load(l, "test", role)) == len(e)
        for i in random.Random(1).sample(range(len(e)), 60):
            srcs.append(e[i])
            for l in mt: mt[l].append(load(l, "test", role)[i])
    name = "facebook/nllb-200-distilled-600M"
    tok = AutoTokenizer.from_pretrained(name, src_lang="eng_Latn", local_files_only=True)
    m = AutoModelForSeq2SeqLM.from_pretrained(name, torch_dtype=torch.float16, local_files_only=True).cuda().eval()
    def translate(texts, src, tgt):
        tok.src_lang = src; res = []
        for i in range(0, len(texts), 16):
            b = tok(texts[i:i+16], return_tensors="pt", padding=True, truncation=True, max_length=96).to("cuda")
            with torch.no_grad(): g = m.generate(**b, forced_bos_token_id=tok.convert_tokens_to_ids(tgt), num_beams=4, max_new_tokens=int(1.6 * b["input_ids"].shape[1] + 8), no_repeat_ngram_size=3, repetition_penalty=1.2)
            res += tok.batch_decode(g, skip_special_tokens=True)
        return res
    mt["hi"] = translate(srcs, "eng_Latn", "hin_Deva")          # calibration: same NLLB, Hindi
    def chrf(h, r, n=6, beta=2):
        def ng(s, k): s = s.replace(" ", ""); return collections.Counter(s[i:i+k] for i in range(len(s) - k + 1))
        P = R = 0; c = 0
        for k in range(1, n + 1):
            a, b = ng(h, k), ng(r, k)
            if not a or not b: continue
            ov = sum((a & b).values()); P += ov / sum(a.values()); R += ov / sum(b.values()); c += 1
        if not c: return 0.0
        P, R = P / c, R / c
        return 0.0 if P + R == 0 else 100 * (1 + beta ** 2) * P * R / (beta ** 2 * P + R)
    res = {}
    for l in ("mr", "gu", "hi"):
        back = translate(mt[l], {"mr": "mar_Deva", "gu": "guj_Gujr", "hi": "hin_Deva"}[l], "eng_Latn")
        sc = [chrf(b, s) for b, s in zip(back, srcs)]
        lat = sum(1 for t in mt[l] if re.search(r"[A-Za-z]", t)) / len(mt[l])
        wr = [len(t.split()) / max(len(s.split()), 1) for t, s in zip(mt[l], srcs)]
        import statistics as _st
        kept = [i for i in range(len(sc)) if (lambda w: w and len(w) <= 30 and max(collections.Counter(w).values()) < 4)(norm(mt[l][i], l if l != "hi" else "hi").split())]
        res[l] = {"n": len(srcs), "roundtrip_chrF_mean": sum(sc) / len(sc), "roundtrip_chrF_median": _st.median(sc), "kept_share": len(kept) / len(sc), "kept_chrF_mean": _st.mean([sc[i] for i in kept]), "kept_chrF_median": _st.median([sc[i] for i in kept]), "share_chrF_below_25": sum(x < 25 for x in sc) / len(sc), "median_word_ratio_vs_english": _st.median(wr), "share_runaway_ratio_gt_3": sum(x > 3 for x in wr) / len(wr), "per_sentence": [{"en": srcs[i], l: mt[l][i], "back": back[i], "chrF": round(sc[i], 1)} for i in range(len(sc))], "share_chrF_below_40": sum(x < 40 for x in sc) / len(sc),
                  "share_with_latin_letters": lat, "mean_word_ratio_vs_english": sum(wr) / len(wr),
                  "examples_worst": [{"en": srcs[i], l: mt[l][i], "back": back[i], "chrF": round(sc[i], 1)} for i in sorted(range(len(sc)), key=lambda i: sc[i])[:5]]}
        print(l, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res[l].items() if k not in ("examples_worst", "per_sentence")}, flush=True)
    json.dump(res, open("results/step1_diagnose_gpu.json", "w"), indent=1, ensure_ascii=False)
