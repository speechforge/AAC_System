"""Step 17 (review point 5): the English comparison with the baseline paper's method (Gaines & Vertanen 2025, OPT) redone with
uncertainty. The earlier table (RESULTS_vs_baseline.txt) used 40+40 test sentences, one run, one adaptation seed, no interval.
Here:
  * FULL English test sets (403 AAC + 402 caregiver sentences), the same run_stream protocol as Steps 2-5 (5 suggestions,
    1 keystroke to select), the SAME candidate pool for every system (300 most frequent words matching the typed letters +
    5 character-model completions, predictor_v2.LangModel.candidates).
  * OPT used as the baseline paper uses an LM for word prediction: every candidate word scored by its log-probability after
    the sentence so far (our re-implementation; the baseline's own models and test data are not public).
  * OPT-125m adapted on our train split with 3 seeds (0, 1, 2): mean and range across seeds, plus each seed's interval.
  * Paired bootstrap 95 % CI over sentences (1,000 resamples, exp_final.boot_ci) of every system against ours.
  * Speed: 5 repeated runs of 200 fresh (uncached) next-word queries per system, cuda-synchronised; per run the median and p95;
    reported as the median over runs and the min-max range across runs. Shared GPU: other jobs run on it.
   python exp_step17_baseline_ci.py"""
import sys, json, time, random, statistics, gc, os, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from lib import *
from exp_final import run_stream, boot_ci
import predictor_v2 as P, lm_rerank as L
L.CACHE_MAX = 10**7
OPT_BATCH = int(os.environ.get("OPT_BATCH", "32"))   # candidates per OPT forward pass (memory vs speed; same scores up to fp16 rounding)
L.CHUNK = int(os.environ.get("LM_CHUNK", str(L.CHUNK)))
lang = "en"; t_start = time.time()
train = sents(lang, "train"); dev = sents(lang, "dev"); tests = {k: sents(lang, "test", (k,)) for k in ("aac", "care")}
m = P.LangModel(lang, train, cov=True); e = make_engine(train, lang); pool300 = Pool(train, 300)


class SamePool:                                  # one candidate pool for every system
    def get(self, prefix): return m.candidates(prefix)
POOL = SamePool()
res = {"protocol": __doc__, "n_test": {k: len(v) for k, v in tests.items()}, "systems": {}, "speed_ms_per_query": {}}
per = {}
# run 2 (after a CUDA OOM in run 1): per-sentence rows are checkpointed, finished systems are skipped on a restart
ROWS = "results/step17_rows.json"
if os.path.exists(ROWS):
    ck = json.load(open(ROWS)); per.update({k: {s_: [tuple(x) for x in v] for s_, v in d.items()} for k, d in ck["per"].items()})
    res["systems"].update(ck["systems"]); res["speed_ms_per_query"].update(ck["speed"])
def checkpoint():
    json.dump(dict(per=per, systems=res["systems"], speed=res["speed_ms_per_query"]), open(ROWS, "w"))
def free_gpu():
    gc.collect(); torch.cuda.empty_cache()


def evaluate(name, scorer):
    if name in per: print("skip (checkpoint)", name, flush=True); return
    t0 = time.time(); r = {}; per[name] = {}
    for k, v in tests.items():
        s, p, h = run_stream(v, scorer, POOL); r[k] = dict(ksr_pct=round(s, 3), top1=h[1], top5=h[5]); per[name][k] = p
    r["avg_ksr"] = round((r["aac"]["ksr_pct"] + r["care"]["ksr_pct"]) / 2, 3); r["wall_s"] = round(time.time() - t0)
    res["systems"][name] = r; print(name, r, flush=True); json.dump(res, open("results/step17_baseline_ci.json", "w"), indent=1); checkpoint()


# ---------------- our systems (the shipped code) ----------------
def ours_cpu(ctx, cands): return m.score(list(ctx), cands)
def ours_gpu(ctx, cands):
    sc = m.score(list(ctx), cands); r = sorted(zip(sc, cands), key=lambda x: -x[0])
    rr = L.rerank(lang, list(ctx), r, k=50)
    LMCOUNT[rr is not None] += 1; rr = rr or r; d = {w: s for s, w in rr}
    return [d.get(w, -1.0) for w in cands]
LMCOUNT = {True: 0, False: 0}                    # re-ranker used / fell back to CPU (must be 0 fallbacks)
inf_old = inf_shipped_scorer(e, pool300)
def ours_shipped(ctx, cands):                    # the old shipped infinity-gram, on the same pool
    return inf_old(list(ctx), cands)
evaluate("OURS old shipped infinity-gram (CPU)", ours_shipped)
evaluate("OURS predictor_v2 (CPU)", ours_cpu)


# ---------------- the baseline method: OPT scores every candidate word ----------------
def lexicon_scorer(mod, tok):
    cache = {}
    @torch.no_grad()
    def score(ctx, cands):
        sc = cache.setdefault(tuple(ctx), {}); miss = [w for w in cands if w not in sc]
        text = " ".join(ctx); base = [tok.bos_token_id] + (tok(text, add_special_tokens=False)["input_ids"] if text else [])
        for i in range(0, len(miss), OPT_BATCH):
            ch = miss[i:i + OPT_BATCH]; ws = [tok((" " if ctx else "") + w, add_special_tokens=False)["input_ids"] for w in ch]
            Lm = len(base) + max(map(len, ws)); ids = torch.full((len(ch), Lm), tok.pad_token_id); att = torch.zeros((len(ch), Lm), dtype=torch.long)
            for j, w in enumerate(ws): s_ = base + w; ids[j, :len(s_)] = torch.tensor(s_); att[j, :len(s_)] = 1
            lp = torch.log_softmax(mod(input_ids=ids.cuda(), attention_mask=att.cuda()).logits[:, len(base) - 1:].float(), -1)
            for j, w in enumerate(ws): sc[ch[j]] = sum(lp[j, k, t].item() for k, t in enumerate(w))
        return [sc[w] for w in cands]
    score.cache = cache
    return score


def adapt(name, seed):                           # same recipe as experiments_vs_baseline/exp_llm.py (5 epochs, best dev loss)
    random.seed(seed); torch.manual_seed(seed)
    tok = AutoTokenizer.from_pretrained(name); mod = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float32).cuda()
    opt = torch.optim.AdamW(mod.parameters(), lr=3e-5, weight_decay=0.01)
    def batches(data, bs):
        d = data[:]; random.shuffle(d)
        for i in range(0, len(d), bs):
            enc = tok(d[i:i + bs], return_tensors="pt", padding=True); lab = enc["input_ids"].clone(); lab[enc["attention_mask"] == 0] = -100
            yield enc.to("cuda"), lab.to("cuda")
    def devloss():
        mod.eval(); tot = n = 0
        with torch.no_grad():
            for enc, lab in batches(dev, 32):
                o = mod(**enc, labels=lab); k = (lab != -100).sum().item(); tot += o.loss.item() * k; n += k
        mod.train(); return tot / n
    best = (devloss(), 0); sd = {k: v.clone() for k, v in mod.state_dict().items()}; mod.train()
    for ep in range(1, 6):
        for enc, lab in batches(train, 16):
            loss = mod(**enc, labels=lab).loss; loss.backward(); opt.step(); opt.zero_grad()
        dl = devloss()
        if dl < best[0]: best = (dl, ep); sd = {k: v.clone() for k, v in mod.state_dict().items()}
    mod.load_state_dict(sd); mod.half().eval(); return tok, mod, best


# speed queries: fresh contexts from the caregiver test set
rq = random.Random(5); QUERIES = []
for s_ in rq.sample(tests["care"], 200):
    ws = s_.split(); i = rq.randrange(len(ws)); QUERIES.append((ws[:i], ws[i][:rq.randrange(0, max(len(ws[i]), 1))]))


def speed(name, make_fn, runs=5):
    if name in res["speed_ms_per_query"]: print("skip speed (checkpoint)", name, flush=True); return
    meds, p95s = [], []
    for run in range(runs):
        fn = make_fn(); ts = []
        for j, (ctx, pre) in enumerate(QUERIES):
            cands = m.candidates(pre)
            if torch.cuda.is_available(): torch.cuda.synchronize()
            t = time.perf_counter(); fn(ctx, cands)
            if torch.cuda.is_available(): torch.cuda.synchronize()
            ts.append(1000 * (time.perf_counter() - t))
        ts.sort(); meds.append(ts[len(ts) // 2]); p95s.append(ts[int(.95 * len(ts))])
    res["speed_ms_per_query"][name] = dict(median_over_runs=round(statistics.median(meds), 3), range_of_run_medians=[round(min(meds), 3), round(max(meds), 3)],
                                           p95_median_over_runs=round(statistics.median(p95s), 3), runs=runs, queries_per_run=len(QUERIES))
    print("speed", name, res["speed_ms_per_query"][name], flush=True); json.dump(res, open("results/step17_baseline_ci.json", "w"), indent=1); checkpoint()


def fresh_lm_cache():
    L._cache.clear()                             # every run starts uncached
    return ours_gpu
def fresh_cpu():
    m._cand_cache.clear(); m._pool_cache.clear(); m.cm.memo.clear(); return ours_cpu
speed("OURS predictor_v2 (CPU)", fresh_cpu)

for name in ("facebook/opt-125m", "facebook/opt-350m"):
    tok = AutoTokenizer.from_pretrained(name); mod = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float16).cuda().eval()
    evaluate(f"BASELINE {name} pretrained", lexicon_scorer(mod, tok))
    speed(f"BASELINE {name} pretrained", lambda: lexicon_scorer(mod, tok))
    del mod; free_gpu()
seeds = {}
for seed in (0, 1, 2):
    nm = f"BASELINE facebook/opt-125m adapted on our train split, seed {seed}"
    if nm in per and (seed or "BASELINE facebook/opt-125m adapted" in res["speed_ms_per_query"]):
        seeds[seed] = res["systems"][nm]["avg_ksr"]; continue
    tok, mod, best = adapt("facebook/opt-125m", seed)
    evaluate(nm, lexicon_scorer(mod, tok)); res["systems"][nm]["best_epoch_dev_loss"] = [best[1], round(best[0], 4)]
    if seed == 0: speed("BASELINE facebook/opt-125m adapted", lambda: lexicon_scorer(mod, tok))
    seeds[seed] = res["systems"][nm]["avg_ksr"]; del mod; free_gpu()
# our GPU system LAST, so BLOOM never shares the GPU with an OPT model in this process
evaluate("OURS predictor_v2 + adapted BLOOM-560m re-ranker K50 (GPU)", ours_gpu)
res["reranker_calls"] = {"used": LMCOUNT[True], "fell_back_to_cpu": LMCOUNT[False], "lm_status": L.status()}
print("re-ranker calls", res["reranker_calls"], flush=True)
speed("OURS predictor_v2 + BLOOM re-ranker K50 (GPU)", lambda: (fresh_cpu(), fresh_lm_cache())[1])
res["opt125m_adapted_across_seeds"] = dict(mean=round(statistics.mean(seeds.values()), 3), min=min(seeds.values()), max=max(seeds.values()), per_seed=seeds)

# paired intervals: every system against our final GPU system and against our CPU system
ref_gpu, ref_cpu = "OURS predictor_v2 + adapted BLOOM-560m re-ranker K50 (GPU)", "OURS predictor_v2 (CPU)"
res["paired_95ci_pp"] = {}
for nm in per:
    for ref in (ref_gpu, ref_cpu):
        if nm != ref:
            res["paired_95ci_pp"][f"{ref} minus {nm}"] = {k: [round(x, 2) for x in boot_ci(per[nm][k], per[ref][k])] for k in tests}
res["seconds"] = round(time.time() - t_start); json.dump(res, open("results/step17_baseline_ci.json", "w"), indent=1)
print(json.dumps(res["paired_95ci_pp"], indent=1)); print("done", res["seconds"], "s")
