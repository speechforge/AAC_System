"""Improvement experiments (plan steps 1-3): (1) drop selected-word exclusion, (2) hybrid = infinity-gram + char 12-gram (CPU, all 4 langs),
(3) hybrid = infinity-gram + in-domain adapted OPT-125m re-ranker (English, GPU, subsample)."""
import sys, json, math, random
from lib import *
def softnorm(sc):
    m = max(sc); e = [math.exp(x - m) for x in sc]; z = sum(e); return [x / z for x in e]
def noexcl_scorer(e, alpha=0.4):
    uni = e.unigrams_hi if e.tag == "hi" else e.unigrams_en; T = sum(uni.values())
    def sc(ctx, cands):
        d = inf_dist(e, ctx, alpha); raw = [d.get(w, 0.0) + 1e-6 * uni.get(w, 0) / T for w in cands]; z = sum(raw); return [x / z for x in raw]
    return sc
def mix(sa, sb, w):
    def sc(ctx, cands):
        a, b = sa(ctx, cands), sb(ctx, cands); return [w * x + (1 - w) * y for x, y in zip(a, b)]
    return sc
def char_prob_scorer(cm):
    f = charlm_scorer(cm)
    return lambda ctx, cands: softnorm(f(ctx, cands))
mode = sys.argv[1]
out = {}
if mode == "cpu":
    for lang in sys.argv[2:]:
        train = sents(lang, "train"); dev = sents(lang, "dev"); tests = {"aac": sents(lang, "test", ("aac",)), "care": sents(lang, "test", ("care",))}
        cm = CharNgram(12).train(train); e = make_engine(train, lang); pool = Pool(train, 300)
        base = noexcl_scorer(e); chs = char_prob_scorer(cm)
        best = (-1, None)
        for w in (0.2, 0.4, 0.5, 0.6, 0.8):        # tune mixing weight on dev
            s = ksr(dev[:200], predictor_from_scorer(mix(base, chs, w), pool))[0]
            if s > best[0]: best = (s, w)
        w = best[1]; out[lang] = {"mix_weight_infgram": w, "dev_ksr": best[0], "systems": {}}
        for nm, sc in (("shipped infinity-gram", inf_shipped_scorer(e, pool)), ("step1: no selected-word exclusion", base), ("char 12-gram", chs), ("step2: infinity-gram + char 12-gram hybrid", mix(base, chs, w))):
            r = {}
            for k, v in tests.items():
                s, ka, kp, hits, nw = ksr(v, predictor_from_scorer(sc, pool)); r[k] = dict(ksr_pct=s, top5=hits[5], top10=hits[10])
            r["avg_ksr"] = (r["aac"]["ksr_pct"] + r["care"]["ksr_pct"]) / 2; out[lang]["systems"][nm] = r
            print(lang, nm, round(r["avg_ksr"], 2), flush=True)
        json.dump(out, open("results/improve_cpu_" + "_".join(sys.argv[2:]) + ".json", "w"), indent=1)
else:   # gpu: English, adapted OPT-125m re-ranker
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    random.seed(0); lang = "en"
    train = sents(lang, "train"); dev = sents(lang, "dev"); full = {"aac": sents(lang, "test", ("aac",)), "care": sents(lang, "test", ("care",))}
    ksr_set = {k: random.Random(1).sample(v, 80)[:40] for k, v in full.items()}      # same 40+40 sentences as exp_llm.py
    name = "facebook/opt-125m"; tok = AutoTokenizer.from_pretrained(name); m = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float32).cuda()
    opt = torch.optim.AdamW(m.parameters(), lr=3e-5, weight_decay=0.01)
    def batches(data, bs):
        d = data[:]; random.shuffle(d)
        for i in range(0, len(d), bs):
            enc = tok(d[i:i+bs], return_tensors="pt", padding=True); lab = enc["input_ids"].clone(); lab[enc["attention_mask"] == 0] = -100; yield enc.to("cuda"), lab.to("cuda")
    m.train()
    for enc, lab in batches(train, 16): m(**enc, labels=lab).loss.backward(); opt.step(); opt.zero_grad()   # 1 epoch = best dev epoch in exp_llm.py
    m.half().eval()
    cache = {}
    @torch.no_grad()
    def opt_scorer(ctx, cands):
        key = tuple(ctx); sc = cache.setdefault(key, {}); miss = [w for w in cands if w not in sc]
        text = " ".join(ctx); base_ids = [tok.bos_token_id] + (tok(text, add_special_tokens=False)["input_ids"] if text else [])
        for i in range(0, len(miss), 48):
            ch = miss[i:i+48]; ws = [tok((" " if ctx else "") + w, add_special_tokens=False)["input_ids"] for w in ch]
            L = len(base_ids) + max(map(len, ws)); ids = torch.full((len(ch), L), tok.pad_token_id); att = torch.zeros((len(ch), L), dtype=torch.long)
            for j, w in enumerate(ws): s_ = base_ids + w; ids[j, :len(s_)] = torch.tensor(s_); att[j, :len(s_)] = 1
            lp = torch.log_softmax(m(input_ids=ids.cuda(), attention_mask=att.cuda()).logits[:, len(base_ids)-1:].float(), -1)
            for j, w in enumerate(ws): sc[ch[j]] = sum(lp[j, k, t].item() for k, t in enumerate(w))
        return softnorm([sc[w] for w in cands])
    cm = CharNgram(12).train(train); e = make_engine(train, lang); pool = Pool(train, 300); base = noexcl_scorer(e)
    best = (-1, None)
    for w in (0.2, 0.4, 0.6):
        s = ksr(dev[:30], predictor_from_scorer(mix(base, opt_scorer, w), pool))[0]; print("dev w", w, round(s, 2), flush=True)
        if s > best[0]: best = (s, w)
    w = best[1]; res = {"mix_weight_infgram": w, "dev_ksr_30_sents": best[0], "n_ksr_sents_per_set": 40, "systems": {}}
    for nm, sc in (("shipped infinity-gram", inf_shipped_scorer(e, pool)), ("step1: no selected-word exclusion", base), ("adapted OPT-125m alone", opt_scorer), ("step3: infinity-gram + adapted OPT-125m hybrid", mix(base, opt_scorer, w))):
        r = {}
        for k, v in ksr_set.items():
            s, ka, kp, hits, nw = ksr(v, predictor_from_scorer(sc, pool)); r[k] = dict(ksr_pct=s, top5=hits[5], top10=hits[10])
        r["avg_ksr"] = (r["aac"]["ksr_pct"] + r["care"]["ksr_pct"]) / 2; res["systems"][nm] = r; print(nm, round(r["avg_ksr"], 2), flush=True)
    json.dump({"en": res}, open("results/improve_gpu_en.json", "w"), indent=1)
