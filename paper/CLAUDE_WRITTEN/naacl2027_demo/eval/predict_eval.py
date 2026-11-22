#!/usr/bin/env python3
"""Held-out next-word prediction: deployed infinity-gram engine vs. frequency / bigram / trigram baselines.

Data: english_AAC_Dataset / hindi_AAC_Dataset (3 batches x 100 source conversations; each source appears in the
      *_transformed and *_augmented files at the same row index => the split unit is the SOURCE conversation).
Split: source index k = 100*batch + row; held out if k % 5 == 0 (60 sources/language), the rest is training.
Train: both transformed+augmented rows of the 240 training sources (all speakers, as the deployed engine ingests them)
       + the engine's built-in seed corpus.  The held-out sources contribute NOTHING to any model.
Test items: AAC-user utterances (`is_aac_user`) of the held-out sources, taken from the *_transformed file only
            (utterance_intended, i.e. the noise-free target). One item per (utterance, position j>=1):
            context = tokens[:j], target = tokens[j].  Targets outside the training vocabulary count as misses.
All systems use the same tokenization, train tokens, candidate exclusion of already-selected words, and top-10 lists.
Metrics: hit@1/3/5, MRR@10; 95% CIs and paired differences by cluster bootstrap over source conversations."""
import json, sys, glob, pathlib, tempfile, collections, hashlib, time
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "indic-generative-aac/backend"))
import infinity_gram as IG  # noqa: E402  (importing builds the deployed singleton once; unused here)

CFG = json.loads((HERE / "config.json").read_text())
BATCHES = ["20250513_215220", "20250514_123555", "20250515_080705"]
LOC = {"en": ("english_AAC_Dataset", "en-US"), "hi": ("hindi_AAC_Dataset", "hi-IN")}
K_HOLD = CFG["prediction_split"]["holdout_every_kth_source_conversation"]
OFF = CFG["prediction_split"]["offset"]


def load_rows(lang, kind):
    d, loc = LOC[lang]
    rows = {}
    for bi, b in enumerate(BATCHES):
        p = ROOT / d / f"batch_output_{loc}_{b}_{kind}.jsonl"
        for ri, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
            if line.strip():
                rows[bi * 100 + ri] = json.loads(line)
    return rows


def tokenize(eng, text, lang):
    return eng._clean_tokens(text, lang)


def build(lang):
    tr, au = load_rows(lang, "transformed"), load_rows(lang, "augmented")
    # alignment check: identical (speaker, is_aac_user) turn signature at the same index.
    # (Scene text cannot be compared for Hindi: each file was machine-translated separately.)
    sig = lambda r: [(t["speaker"], t.get("is_aac_user")) for t in r["conversation"]]
    mism = [k for k in tr if sig(tr[k]) != sig(au.get(k, {"conversation": []}))]
    assert not mism, f"transformed/augmented misaligned at {mism[:5]}"
    train_dir = pathlib.Path(tempfile.mkdtemp(prefix="igtrain_"))
    for d, loc in (("english_AAC_Dataset", "en-US"), ("hindi_AAC_Dataset", "hi-IN")):
        (train_dir / d).mkdir()
    out = train_dir / LOC[lang][0] / f"train_{lang}.jsonl"
    n_train_sources = 0
    with out.open("w", encoding="utf-8") as f:
        for k in sorted(tr):
            if k % K_HOLD == OFF:
                continue
            n_train_sources += 1
            f.write(json.dumps(tr[k], ensure_ascii=False) + "\n")
            f.write(json.dumps(au[k], ensure_ascii=False) + "\n")
    eng = IG.AACInfinityGramEngine(data_root=str(train_dir))
    # parallel token lists for baselines (same ingestion rule as the engine)
    train_sents = [list(s) for s in IG_SEEDS[lang]]
    for line in out.read_text(encoding="utf-8").splitlines():
        for turn in json.loads(line).get("conversation", []):
            tk = tokenize(eng, turn.get("utterance_intended") or turn.get("utterance", ""), lang)
            if tk:
                train_sents.append(tk if lang == "hi" else [t.lower() for t in tk])
    items = []
    for k in sorted(tr):
        if k % K_HOLD != OFF:
            continue
        for turn in tr[k]["conversation"]:
            if not turn.get("is_aac_user"):
                continue
            tk = tokenize(eng, turn.get("utterance_intended") or turn.get("utterance", ""), lang)
            tk = tk if lang == "hi" else [t.lower() for t in tk]
            for j in range(1, len(tk)):
                items.append((k, tuple(tk[:j]), tk[j], tuple(tk)))
    return eng, train_sents, items, n_train_sources


IG_SEEDS = {"en": IG.SEED_AAC_CORPUS_EN, "hi": IG.SEED_AAC_CORPUS_HI}


class NGram:
    """Stupid-backoff n-gram over the same train sentences. order=1 -> unigram frequency."""
    def __init__(self, sents, order):
        self.order = order
        self.c = [collections.defaultdict(collections.Counter) for _ in range(order)]
        for s in sents:
            for i, w in enumerate(s):
                for n in range(order):             # context length n
                    if i - n >= 0:
                        self.c[n][tuple(s[i - n:i])][w] += 1
        self.vocab = set(self.c[0][()].keys())

    def predict(self, ctx, k=10, alpha=0.4):
        sel = set(ctx); cand = collections.defaultdict(float); w = 1.0
        for n in range(min(self.order - 1, len(ctx)), -1, -1):
            dist = self.c[n].get(tuple(ctx[len(ctx) - n:]) if n else (), None)
            if dist:
                tot = sum(dist.values())
                for x, cnt in dist.items():
                    if x not in sel:
                        cand[x] = max(cand[x], w * cnt / tot)   # stupid backoff: best (discounted) estimate
            w *= alpha
        return [x for x, _ in sorted(cand.items(), key=lambda t: (-t[1], t[0]))[:k]]


def eval_system(name, fn, items, vocab):
    hit1 = []; hit3 = []; hit5 = []; rr = []; clusters = []
    for k, ctx, tgt, _ in items:
        pred = fn(list(ctx))
        rank = pred.index(tgt) + 1 if tgt in pred else None
        hit1.append(rank == 1); hit3.append(bool(rank and rank <= 3)); hit5.append(bool(rank and rank <= 5))
        rr.append(1.0 / rank if rank else 0.0); clusters.append(k)
    return dict(name=name, hit1=np.array(hit1, float), hit3=np.array(hit3, float), hit5=np.array(hit5, float),
                mrr=np.array(rr), cl=np.array(clusters))


def boot(sysres, items_cl, B, rng):
    """Return B resampled cluster-ratio estimates per metric for each system (same resamples => paired)."""
    ucl = np.unique(items_cl); idx = {c: i for i, c in enumerate(ucl)}
    ci = np.array([idx[c] for c in items_cl]); n = np.bincount(ci, minlength=len(ucl)).astype(float)
    draws = rng.integers(0, len(ucl), size=(B, len(ucl)))
    res = {}
    for s in sysres:
        res[s["name"]] = {}
        for m in ("hit1", "hit3", "hit5", "mrr"):
            sums = np.bincount(ci, weights=s[m], minlength=len(ucl))
            res[s["name"]][m] = sums[draws].sum(1) / n[draws].sum(1)
    return res


def main():
    rng = np.random.default_rng(CFG["bootstrap"]["seed"]); B = CFG["bootstrap"]["resamples"]
    out = {}
    for lang in ("en", "hi"):
        t0 = time.time()
        eng, train_sents, items, n_tr = build(lang)
        uni, bi, tri = NGram(train_sents, 1), NGram(train_sents, 2), NGram(train_sents, 3)
        vocab = uni.vocab
        systems = [("unigram_frequency", lambda c, m=uni: m.predict(c)), ("bigram_backoff", lambda c, m=bi: m.predict(c)),
                   ("trigram_backoff", lambda c, m=tri: m.predict(c)),
                   ("infinity_gram_deployed", lambda c, e=eng, l=lang: [p["word"] for p in e.predict_next(c, language=l, top_k=10)])]
        res = [eval_system(n, f, items, vocab) for n, f in systems]
        bs = boot(res, np.array([i[0] for i in items]), B, rng)
        seeds = set(tuple(s) for s in IG_SEEDS[lang])
        full_utts = {i[3] for i in items}
        train_utts = {tuple(s) for s in train_sents}
        dup = sum(1 for u in full_utts if u in train_utts)
        oov = float(np.mean([t not in vocab for _, _, t, _ in items]))
        o = dict(language=lang, n_items=len(items), n_clusters=len(set(i[0] for i in items)), n_train_sources=n_tr,
                 n_train_sentences=len(train_sents), vocab=len(vocab), oov_target_rate=round(oov, 4),
                 n_test_utterances=len(full_utts), test_utterances_seen_verbatim_in_train=dup,
                 test_utterances_in_seed_corpus=len(full_utts & seeds), systems={})
        for s in res:
            e = {}
            for m in ("hit1", "hit3", "hit5", "mrr"):
                d = bs[s["name"]][m]
                e[m] = dict(value=round(float(s[m].mean()), 4), ci95=[round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)])
            o["systems"][s["name"]] = e
        o["paired_vs_infinity_gram"] = {}
        for s in res:
            if s["name"] == "infinity_gram_deployed":
                continue
            o["paired_vs_infinity_gram"][s["name"]] = {}
            for m in ("hit1", "hit3", "hit5", "mrr"):
                diff = bs["infinity_gram_deployed"][m] - bs[s["name"]][m]
                est = float([x for x in res if x["name"] == "infinity_gram_deployed"][0][m].mean() - s[m].mean())
                o["paired_vs_infinity_gram"][s["name"]][m] = dict(diff=round(est, 4), ci95=[round(float(np.percentile(diff, 2.5)), 4), round(float(np.percentile(diff, 97.5)), 4)])
        o["seconds"] = round(time.time() - t0, 1)
        out[lang] = o
        print(json.dumps(o, ensure_ascii=False, indent=1))
    (HERE / "results/prediction.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
