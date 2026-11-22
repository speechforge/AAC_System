#!/usr/bin/env python3
"""Evaluate the project's trained HMMs on the SAME held-out contexts as predict_eval.py, through the deployed scoring code
(indic-generative-aac/backend/hmm.py: AACHMM.predict_next with the infinity-gram engine disabled).

  gutenberg_hmm_english : the shipped English HMM (hmm_model.pkl; trained by backend/train_hmm_large.py on Project Gutenberg text; no overlap with the AAC dialogues)
  hindi_hmm_retrained   : the Hindi AAC HMM RETRAINED with the project's own train_hindi_hmm_dataset.py on the TRAINING sources only
                          (the shipped hmm_hindi.pkl was trained on all Hindi dialogues, so evaluating it on held-out sources would leak)
  dual HMM-1 (4-gram)   : NOT evaluated here -- the trained object is a Git LFS file that is not present (see FINAL_CONTEXT.md)
Usage: python hmm_eval.py --gutenberg /path/to/hmm_model.pkl"""
import sys, json, pickle, hashlib, pathlib, tempfile, importlib, collections, io, contextlib
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "indic-generative-aac/backend")); sys.path.insert(0, str(ROOT))
import predict_eval as PE                                  # same split, same items, same bootstrap
CFG = PE.CFG
gpath = sys.argv[sys.argv.index("--gutenberg") + 1] if "--gutenberg" in sys.argv else "/home/linux/Videos/AAC_System_Jaydeep/indic-generative-aac/backend/hmm_model.pkl"

with contextlib.redirect_stdout(io.StringIO()):
    import hmm as H                                        # deployed module (prints while loading; silenced)
    base = H.AACHMM()
base.infinity_gram = None                                  # evaluate the Markov path only

def english_gutenberg():
    raw = open(gpath, "rb").read(); sha = hashlib.sha256(raw).hexdigest(); g = pickle.loads(raw)
    e = H.AACHMM.__new__(H.AACHMM)
    e.__dict__.update(base.__dict__)
    e.infinity_gram = None
    e.bigrams = collections.defaultdict(collections.Counter, g["bigrams"]); e.trigrams = collections.defaultdict(collections.Counter, g["trigrams"])
    e.fourgrams = {}; e.unigrams = collections.Counter(); e.start_priors = collections.Counter(); e.hindi_bigrams = {}
    return e, dict(path=gpath, sha256=sha, bytes=len(raw), sentences=g["sentence_count"], bigram_states=len(g["bigrams"]), trigram_states=len(g["trigrams"]))

def hindi_retrained(train_rows_dir):
    mod = importlib.import_module("train_hindi_hmm_dataset")
    mod.DATASET_DIR = str(train_rows_dir); mod.OUTPUT_PATH = str(train_rows_dir / "hmm_hindi_retrained.pkl")
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        mod.build_hmm()
    d = pickle.load(open(mod.OUTPUT_PATH, "rb"))
    e = H.AACHMM.__new__(H.AACHMM); e.__dict__.update(base.__dict__); e.infinity_gram = None
    e.hindi_priors = collections.Counter(d["priors"]); e.hindi_bigrams = collections.defaultdict(collections.Counter, {k: collections.Counter(v) for k, v in d["bigrams"].items()})
    e.hindi_trigrams = collections.defaultdict(collections.Counter, {k: collections.Counter(v) for k, v in d["trigrams"].items()}); e.hindi_emojis = d["emojis"]; e.hindi_vocab = d["vocab"]
    return e, dict(sentences=d["sentence_count"], vocab=len(d["vocab"]), bigram_contexts=len(d["bigrams"]), trigram_contexts=len(d["trigrams"]))

def hindi_train_dir():
    """Training sources only, in the layout train_hindi_hmm_dataset.py expects (*transformed.jsonl)."""
    tr = PE.load_rows("hi", "transformed"); d = pathlib.Path(tempfile.mkdtemp(prefix="hihmm_"))
    with (d / "batch_output_hi-IN_train_transformed.jsonl").open("w", encoding="utf-8") as f:
        for k in sorted(tr):
            if k % PE.K_HOLD != PE.OFF: f.write(json.dumps(tr[k], ensure_ascii=False) + "\n")
    return d

def unjumble_eval():
    """HMM-2 (AACUnjumbleHMM) exact-match / Kendall tau on held-out English AAC-user utterances of 3-6 words (deterministic shuffle, seed in config)."""
    m = getattr(base, "unjumble_model", None)
    if m is None or not hasattr(m, "unjumble"):
        return dict(status="not_evaluated", reason="hmm2_unjumble_latest.pkl (Git LFS object) not present at dual_hmm_streaming_kit/models/")
    import random
    ig, train_sents, items, n_tr = PE.build("en")
    utts = sorted({i[3] for i in items if 3 <= len(i[3]) <= 6}); rng = random.Random(CFG["bootstrap"]["seed"]); em = 0; tau_sum = 0.0; n = 0; clusters = []
    for u in utts:
        j = list(u)
        for _ in range(10):
            rng.shuffle(j)
            if j != list(u): break
        pred, _ = m.unjumble(j); n += 1; em += int(list(pred) == list(u))
        pos = {w: i for i, w in enumerate(u)}; r = [pos.get(w, i) for i, w in enumerate(pred)]; k = len(r)
        c = sum(1 for a in range(k) for b in range(a + 1, k) if r[a] < r[b]); d = sum(1 for a in range(k) for b in range(a + 1, k) if r[a] > r[b])
        tau_sum += (c - d) / max(1, k * (k - 1) / 2)
    return dict(status="evaluated", n_utterances=n, exact_match=em, exact_match_rate=round(em / n, 4), mean_kendall_tau=round(tau_sum / n, 4))

def run():
    rng = np.random.default_rng(CFG["bootstrap"]["seed"]); B = CFG["bootstrap"]["resamples"]; out = {}
    for lang in ("en", "hi"):
        ig, train_sents, items, n_tr = PE.build(lang)
        uni, bi, tri = PE.NGram(train_sents, 1), PE.NGram(train_sents, 2), PE.NGram(train_sents, 3)
        meta = {}
        extra = []
        if lang == "en":
            hm, meta = english_gutenberg(); name = "gutenberg_hmm_english"
            if len(getattr(base, "fourgrams", {})) > 1000:      # dual-kit HMM-1 loaded from dual_hmm_streaming_kit/models (Git LFS object present)
                meta["hmm1_fourgram_contexts"] = len(base.fourgrams)
                extra.append(("hmm1_dual_kit_4gram", lambda c, h=base, l=lang: [p["word"] for p in h.predict_next(c, language=l, top_k=10)]))
        else:
            hm, meta = hindi_retrained(hindi_train_dir()); name = "hindi_hmm_retrained"
        systems = [(name, lambda c, h=hm, l=lang: [p["word"] for p in h.predict_next(c, language=l, top_k=10)]),
                   ("trigram_backoff", lambda c, m=tri: m.predict(c)),
                   ("infinity_gram_deployed", lambda c, e=ig, l=lang: [p["word"] for p in e.predict_next(c, language=l, top_k=10)])] + extra
        res = [PE.eval_system(n, f, items, None) for n, f in systems]
        bs = PE.boot(res, np.array([i[0] for i in items]), B, rng)
        o = dict(language=lang, n_items=len(items), n_clusters=len(set(i[0] for i in items)), model_meta=meta, systems={}, paired_hmm_minus_infinity_gram={})
        for s in res:
            o["systems"][s["name"]] = {m: dict(value=round(float(s[m].mean()), 4), ci95=[round(float(np.percentile(bs[s["name"]][m], 2.5)), 4), round(float(np.percentile(bs[s["name"]][m], 97.5)), 4)]) for m in ("hit1", "hit3", "hit5", "mrr")}
        inf = [x for x in res if x["name"] == "infinity_gram_deployed"][0]; me = res[0]
        for m in ("hit1", "hit5", "mrr"):
            dd = bs[name][m] - bs["infinity_gram_deployed"][m]
            o["paired_hmm_minus_infinity_gram"][m] = dict(diff=round(float(me[m].mean() - inf[m].mean()), 4), ci95=[round(float(np.percentile(dd, 2.5)), 4), round(float(np.percentile(dd, 97.5)), 4)])
        out[lang] = o
        print(lang, json.dumps({k: (v["hit1"]["value"], v["hit5"]["value"], v["mrr"]["value"]) for k, v in o["systems"].items()}), meta)
    out["hmm2_unjumble"] = unjumble_eval()
    (HERE / "results/hmm_eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__":
    run()
