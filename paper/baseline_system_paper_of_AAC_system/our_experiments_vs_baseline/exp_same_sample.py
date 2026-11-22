"""English: evaluate OUR current systems on EXACTLY the test subsample that the baseline-style OPT rows of Results_10 were measured on
(exp_llm.py: 80+80 sentences for perplexity, the first 40+40 of them for KSR), with the SAME ksr() simulator, so the rows can sit in one table.
   python exp_same_sample.py cpu     -> A shipped, E, E+COV (CPU)
   python exp_same_sample.py gpu     -> adapted BLOOM-560m perplexity (80+80) and system I KSR (K=50 and K=10) on the 40+40"""
import sys, json, math, random, time
from lib import *
from exp_improve_lib import softnorm
from exp_final import capped_scorer, mix
mode = sys.argv[1]; lang = "en"; random.seed(0)
train = sents(lang, "train"); full = {"aac": sents(lang, "test", ("aac",)), "care": sents(lang, "test", ("care",))}
NP, NK = 80, 40; ppl_set = {k: random.Random(1).sample(v, NP) for k, v in full.items()}; ksr_set = {k: ppl_set[k][:NK] for k in full}
src = open("exp_step4.py").read(); exec(src[src.index("class ExtPool"):src.index("def es(base")])
cm = CharNgram(12).train(train); e = make_engine(train, lang); pool = Pool(train, 300); xp = ExtPool(pool, cm, M=5)
tuned = json.load(open(f"results/final_{lang}.json"))[lang]["tuned"]; C, a_ = tuned["step1+5 ctx_cap,alpha"]; wch = tuned["step2 mix_weight_infgram"]
chs = lambda ctx, cands, f=charlm_scorer(cm): softnorm(f(ctx, cands)); cpu = mix(capped_scorer(e, C, a_), chs, wch)
def evalr(scorer, pl):
    r = {}
    for k, v in ksr_set.items():
        s, ka, kp, hits, nw = ksr(v, predictor_from_scorer(scorer, pl)); r[k] = dict(ksr_pct=s, hit_at_empty_prefix_pct=hits, nwords=nw)
    return r
out = {"n_ppl_sents_per_set": NP, "n_ksr_sents_per_set": NK, "systems": {}}
if mode == "cpu":
    for nm, sc, pl in (("A shipped infinity-gram", inf_shipped_scorer(e, pool), pool), ("E improved CPU stack", cpu, pool), ("E+COV (CPU only)", cpu, xp)):
        out["systems"][nm] = {"ksr": evalr(sc, pl)}; print(nm, {k: round(v["ksr_pct"], 2) for k, v in out["systems"][nm]["ksr"].items()}, flush=True)
    json.dump(out, open("results/same_sample_en_cpu.json", "w"), indent=1)
else:
    import torch, torch.nn as nn
    from transformers import AutoTokenizer, AutoModelForCausalLM
    name = "bigscience/bloom-560m"; tok = AutoTokenizer.from_pretrained(name); BOS = tok.bos_token_id if tok.bos_token_id is not None else tok.eos_token_id
    m = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float16).cuda(); m.requires_grad_(False)
    class LoRA(nn.Module):
        def __init__(self, base, r=16, alpha=32):
            super().__init__(); self.base = base; self.A = nn.Parameter(torch.randn(base.in_features, r, device="cuda") * 0.01); self.B = nn.Parameter(torch.zeros(r, base.out_features, device="cuda")); self.s = alpha / r
        def forward(self, x): return self.base(x) + ((x.float() @ self.A) @ self.B * self.s).to(self.base(x).dtype) if False else self.base(x) + ((x.float() @ self.A) @ self.B * self.s).to(x.dtype)
    for mod in list(m.modules()):
        for nm_, ch in list(mod.named_children()):
            if nm_ in ("query_key_value", "dense", "dense_h_to_4h", "dense_4h_to_h") and isinstance(ch, nn.Linear): setattr(mod, nm_, LoRA(ch))
    m.load_state_dict(torch.load(f"results/lora_{lang}.pt"), strict=False); m.eval()
    def seq_logp(texts, bs=4):
        o = []
        with torch.no_grad():
            for i in range(0, len(texts), bs):
                ids = [[BOS] + tok(t, add_special_tokens=False)["input_ids"] for t in texts[i:i+bs]]; L = max(map(len, ids)); x = torch.full((len(ids), L), tok.pad_token_id); a = torch.zeros((len(ids), L), dtype=torch.long)
                for j, s in enumerate(ids): x[j, :len(s)] = torch.tensor(s); a[j, :len(s)] = 1
                lg = m(input_ids=x.cuda(), attention_mask=a.cuda()).logits[:, :-1].float(); o += (torch.log_softmax(lg, -1).gather(-1, x.cuda()[:, 1:, None])[..., 0] * a.cuda()[:, 1:]).sum(1).tolist()
        return o
    ppl = {k: math.exp(-sum(seq_logp(v)) / sum(len(t) for t in v)) for k, v in ppl_set.items()}; ppl["all"] = math.exp(sum(math.log(ppl[k]) for k in ("aac", "care")) / 2); out["bloom_adapted_char_ppl_80+80"] = ppl; print("ppl", ppl, flush=True)
    cache = {}
    @torch.no_grad()
    def lm_scorer(ctx, cands):
        sc = cache.setdefault(tuple(ctx), {}); miss = [w for w in cands if w not in sc]; text = " ".join(ctx); base_ids = [BOS] + (tok(text, add_special_tokens=False)["input_ids"] if text else [])
        if miss:
            ws = [tok((" " if ctx else "") + w, add_special_tokens=False)["input_ids"] for w in miss]; L = len(base_ids) + max(map(len, ws)); ids = torch.full((len(miss), L), tok.pad_token_id); att = torch.zeros((len(miss), L), dtype=torch.long)
            for j, w in enumerate(ws): s_ = base_ids + w; ids[j, :len(s_)] = torch.tensor(s_); att[j, :len(s_)] = 1
            h = m.transformer(input_ids=ids.cuda(), attention_mask=att.cuda()).last_hidden_state[:, len(base_ids)-1:]; lp = torch.log_softmax(m.lm_head(h).float(), -1)
            for j, w in enumerate(ws): sc[miss[j]] = sum(lp[j, k, t].item() for k, t in enumerate(w))
        return softnorm([sc[w] for w in cands])
    W = json.load(open(f"results/step5_{lang}.json"))["chosen_cpu_weight"]
    def inter(K):
        def sc(ctx, cands):
            c = cpu(ctx, cands); idx = sorted(range(len(cands)), key=lambda i: -c[i])[:K]; l = lm_scorer(ctx, [cands[i] for i in idx]); z = sum(c[i] for i in idx); o = [-1.0] * len(cands)
            for r, i in enumerate(idx): o[i] = W * c[i] / z + (1 - W) * l[r]
            return o
        return sc
    for K in (50, 10):
        cache.clear(); nm = f"I = E+COV top-{K} + adapted BLOOM-560m"; out["systems"][nm] = {"ksr": evalr(inter(K), xp)}; print(nm, {k: round(v["ksr_pct"], 2) for k, v in out["systems"][nm]["ksr"].items()}, flush=True)
    json.dump(out, open("results/same_sample_en_gpu.json", "w"), indent=1)
