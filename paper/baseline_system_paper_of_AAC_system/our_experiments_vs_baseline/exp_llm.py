"""Baseline-paper style experiments on English: pretrained OPT (search algorithm) vs in-domain adapted OPT vs our systems,
all trained/evaluated on the same splits and the same test subsample."""
import sys, json, time, math, random, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from lib import *
from charsearch import CharSearchLM, SYMS, SIDX
random.seed(0)
lang = "en"
train = sents(lang, "train"); dev = sents(lang, "dev")
full = {"aac": sents(lang, "test", ("aac",)), "care": sents(lang, "test", ("care",))}
NP, NK = 80, 40
ppl_set = {k: random.Random(1).sample(v, NP) for k, v in full.items()}
ksr_set = {k: ppl_set[k][:NK] for k in full}
res = {"n_ppl_sents_per_set": NP, "n_ksr_sents_per_set": NK, "models": {}}
pool = Pool(train, 300)
lex = pool.ranked

def adapt(name, out):
    tok = AutoTokenizer.from_pretrained(name); m = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float32).cuda()
    opt = torch.optim.AdamW(m.parameters(), lr=3e-5, weight_decay=0.01)
    def batches(data, bs):
        d = data[:]; random.shuffle(d)
        for i in range(0, len(d), bs):
            enc = tok(d[i:i+bs], return_tensors="pt", padding=True); lab = enc["input_ids"].clone(); lab[enc["attention_mask"] == 0] = -100
            yield enc.to("cuda"), lab.to("cuda")
    def devloss():
        m.eval(); tot = n = 0
        with torch.no_grad():
            for enc, lab in batches(dev, 32):
                o = m(**enc, labels=lab); k = (lab != -100).sum().item(); tot += o.loss.item() * k; n += k
        m.train(); return tot / n
    best = (devloss(), None); log = [("epoch0", best[0])]; m.train(); sd = {k: v.clone() for k, v in m.state_dict().items()}
    for ep in range(1, 6):
        for enc, lab in batches(train, 16):
            loss = m(**enc, labels=lab).loss; loss.backward(); opt.step(); opt.zero_grad()
        dl = devloss(); log.append((f"epoch{ep}", dl))
        if dl < best[0]: best = (dl, ep); sd = {k: v.clone() for k, v in m.state_dict().items()}
    m.load_state_dict(sd); m.half().eval(); return tok, m, log, best

def lexicon_scorer(m, tok):
    cache = {}
    @torch.no_grad()
    def score(ctx, cands):
        key = tuple(ctx); sc = cache.setdefault(key, {})
        miss = [w for w in cands if w not in sc]
        text = " ".join(ctx); base = [tok.bos_token_id] + (tok(text, add_special_tokens=False)["input_ids"] if text else [])
        for i in range(0, len(miss), 48):
            chunk = miss[i:i+48]
            ws = [tok((" " if ctx else "") + w, add_special_tokens=False)["input_ids"] for w in chunk]
            L = len(base) + max(map(len, ws))
            ids = torch.full((len(chunk), L), tok.pad_token_id); att = torch.zeros((len(chunk), L), dtype=torch.long)
            for j, w in enumerate(ws):
                s = base + w; ids[j, :len(s)] = torch.tensor(s); att[j, :len(s)] = 1
            lp = torch.log_softmax(m(input_ids=ids.cuda(), attention_mask=att.cuda()).logits[:, len(base)-1:].float(), -1)
            for j, w in enumerate(ws):
                t = 0.0
                for k, tid in enumerate(w): t += lp[j, k, tid].item()
                sc[chunk[j]] = t
        return [sc[w] for w in cands]
    return score

def evaluate(name, tok, m):
    lm = CharSearchLM(m, tok); out = {}
    t0 = time.time(); nf0 = lm.n_forward; nch = 0; ppl = {}
    for k, v in ppl_set.items():
        nll = n = 0
        for s in v: nll -= lm.logp_sentence(s); n += len(s)
        ppl[k] = math.exp(nll / n); nch += n
    ppl["all"] = math.exp(sum(math.log(ppl[k]) * 1 for k in ("aac", "care")) / 2)
    out["perplexity"] = ppl; out["ms_per_char_search_gpu_shared"] = 1000 * (time.time() - t0) / nch; out["forward_per_char"] = (lm.n_forward - nf0) / nch
    pr = predictor_from_scorer(lexicon_scorer(m, tok), pool); out["ksr"] = {}
    for k, v in ksr_set.items():
        s, ka, kp, hits, nw = ksr(v, pr); out["ksr"][k] = dict(ksr_pct=s, hit_at_empty_prefix_pct=hits, nwords=nw)
    out["n_params_M"] = sum(p.numel() for p in m.parameters()) / 1e6
    print(name, json.dumps(out)[:400], flush=True); json.dump(out, open('results/llm_partial_'+name.split('/')[-1]+'.json','w')); return out

for name in ("facebook/opt-125m", "facebook/opt-350m"):
    tok = AutoTokenizer.from_pretrained(name); m = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float16).cuda()
    res["models"][name + " (pretrained)"] = evaluate(name, tok, m); del m; torch.cuda.empty_cache()
tok, m, log, best = adapt("facebook/opt-125m", "x")
res["adaptation_log_dev_token_loss"] = log; res["adaptation_best_epoch"] = best[1]
res["models"]["facebook/opt-125m (adapted on our train split)"] = evaluate("opt-125m-adapted", tok, m); del m; torch.cuda.empty_cache()

# same subsample for our systems and the n-gram baseline
cm = CharNgram(12).train(train); e = make_engine(train, lang)
bd = json.load(open("results/main_en.json"))["inf_dev_tuned"]
lp_inf = inf_logp_fn(e, cm, bd["mu"], bd["eps"])
sysres = {}
for nm, pr, lpf in (("AAC char 12-gram (our-data analogue of baseline n-gram)", predictor_from_scorer(charlm_scorer(cm), pool), lambda s: cm.logp_str("", s)),
                    ("Ours: infinity-gram (shipped predictor)", predictor_from_scorer(inf_shipped_scorer(e, pool), pool), lp_inf)):
    r = {"perplexity": {k: char_ppl(lpf, v)[0] for k, v in ppl_set.items()}, "ksr": {}}
    r["perplexity"]["all"] = math.exp(sum(math.log(r["perplexity"][k]) for k in ("aac", "care")) / 2)
    for k, v in ksr_set.items():
        s, ka, kp, hits, nw = ksr(v, pr); r["ksr"][k] = dict(ksr_pct=s, hit_at_empty_prefix_pct=hits, nwords=nw)
    sysres[nm] = r
res["models"].update(sysres)
json.dump(res, open("results/llm_en.json", "w"), indent=1)
