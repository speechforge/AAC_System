"""Plan step 9 for the LANGUAGE-MODEL system: 5-fold contiguous-block cross-validation of A (shipped), E+COV (CPU) and I (E+COV top-K + adapted BLOOM-560m).
A NEW LoRA adapter is trained on every fold's training part (otherwise the adapter would have seen that fold's test text).
Protocol decisions (compute budget, fixed BEFORE running, not tuned on test): epochs = best epoch of the original dev run; CPU weight w and the CPU knobs = original dev choice;
K = 10 (the deployable setting; the full-test K=50 numbers are in step5); evaluation on every 4th sentence of each fold's test block (same sentences for every system).
   python exp_cv_lm.py <lang>"""
import sys, json, math, random, time, statistics as st, torch, torch.nn as nn
from lib import *
from exp_improve_lib import softnorm
from exp_final import capped_scorer, mix, run_stream, boot_ci
from transformers import AutoTokenizer, AutoModelForCausalLM
lang = sys.argv[1]; K = 10; STRIDE = 4; EPOCHS = {"en": 2, "hi": 3, "mr": None, "gu": None}
EPOCHS = {l: json.load(open(f"results/step2_{l}.json"))["best_epoch"] if l in ("mr", "gu") else EPOCHS[l] for l in EPOCHS}
src5 = json.load(open(f"results/step5_{lang}.json")); W = src5["chosen_cpu_weight"]; ep_n = EPOCHS[lang]
tuned = json.load(open(f"results/final_{lang}.json"))[lang]["tuned"]; C, a_ = tuned["step1+5 ctx_cap,alpha"]; wch = tuned["step2 mix_weight_infgram"]
name = "bigscience/bloom-560m"; tok = AutoTokenizer.from_pretrained(name); BOS = tok.bos_token_id if tok.bos_token_id is not None else tok.eos_token_id
m = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float16).cuda(); m.requires_grad_(False); LORA_ON = [False]; LORAS = []
class LoRA(nn.Module):
    def __init__(self, base, r=16, alpha=32):
        super().__init__(); self.base = base; self.r = r; self.A = nn.Parameter(torch.randn(base.in_features, r, device="cuda") * 0.01); self.B = nn.Parameter(torch.zeros(r, base.out_features, device="cuda")); self.s = alpha / r
    def reset(self):
        with torch.no_grad(): self.A.normal_(0, 0.01); self.B.zero_()
    def forward(self, x):
        y = self.base(x)
        return y + ((x.float() @ self.A) @ self.B * self.s).to(y.dtype) if LORA_ON[0] else y
for mod in list(m.modules()):
    for nm_, ch in list(mod.named_children()):
        if nm_ in ("query_key_value", "dense", "dense_h_to_4h", "dense_4h_to_h") and isinstance(ch, nn.Linear):
            l_ = LoRA(ch); setattr(mod, nm_, l_); LORAS.append(l_)
params = [p for p in m.parameters() if p.requires_grad]
def enc_batch(texts):
    ids = [[BOS] + tok(t, add_special_tokens=False)["input_ids"] for t in texts]; L = max(map(len, ids))
    x = torch.full((len(ids), L), tok.pad_token_id); a = torch.zeros((len(ids), L), dtype=torch.long)
    for i, s in enumerate(ids): x[i, :len(s)] = torch.tensor(s); a[i, :len(s)] = 1
    return x.cuda(), a.cuda()
cache = {}
@torch.no_grad()
def lm_scorer(ctx, cands):
    sc = cache.setdefault(tuple(ctx), {}); miss = [w for w in cands if w not in sc]
    text = " ".join(ctx); base_ids = [BOS] + (tok(text, add_special_tokens=False)["input_ids"] if text else [])
    for i in range(0, len(miss), 64):
        ch = miss[i:i+64]; ws = [tok((" " if ctx else "") + w, add_special_tokens=False)["input_ids"] for w in ch]
        L = len(base_ids) + max(map(len, ws)); ids = torch.full((len(ch), L), tok.pad_token_id); att = torch.zeros((len(ch), L), dtype=torch.long)
        for j, w in enumerate(ws): s_ = base_ids + w; ids[j, :len(s_)] = torch.tensor(s_); att[j, :len(s_)] = 1
        h = m.transformer(input_ids=ids.cuda(), attention_mask=att.cuda()).last_hidden_state[:, len(base_ids)-1:]
        lp = torch.log_softmax(m.lm_head(h).float(), -1)
        for j, w in enumerate(ws): sc[ch[j]] = sum(lp[j, k, t].item() for k, t in enumerate(w))
    return softnorm([sc[w] for w in cands])
src = open("exp_step4.py").read(); exec(src[src.index("class ExtPool"):src.index("def es(base")])

allS = [s for sp in ("train", "dev", "test") for s in sents(lang, sp)]; n = len(allS)
out = {"lang": lang, "n_sentences": n, "K": K, "stride": STRIDE, "epochs": ep_n, "w_cpu": W, "folds": []}; t0 = time.time(); pooled = {"A": [], "E+COV": [], "I": []}
for f in range(5):
    lo, hi = f * n // 5, (f + 1) * n // 5; test = allS[lo:hi][::STRIDE]; train = allS[:lo] + allS[hi:]
    random.seed(f); torch.manual_seed(f); cache.clear()
    for l_ in LORAS: l_.reset()
    LORA_ON[0] = True; opt = torch.optim.AdamW(params, lr=2e-4, weight_decay=0.0); scaler = torch.cuda.amp.GradScaler()
    for ep in range(ep_n):
        d = train[:]; random.shuffle(d); m.train()
        for i in range(0, len(d), 16):
            for j in range(i, min(i + 16, len(d)), 4):
                x, a = enc_batch(d[j:j+4]); lg = m(input_ids=x, attention_mask=a).logits[:, :-1].float()
                loss = nn.functional.cross_entropy(lg.reshape(-1, lg.shape[-1]), x[:, 1:].reshape(-1), ignore_index=tok.pad_token_id) / 4
                scaler.scale(loss).backward()
            scaler.step(opt); scaler.update(); opt.zero_grad()
    m.eval(); t_train = time.time() - t0
    e = make_engine(train, lang); cm = CharNgram(12).train(train); pool = Pool(train, 300); xp = ExtPool(pool, cm, M=5)
    chs = lambda ctx, cands, g=charlm_scorer(cm): softnorm(g(ctx, cands)); cpu = mix(capped_scorer(e, C, a_), chs, wch)
    def inter(ctx, cands):
        c = cpu(ctx, cands); idx = sorted(range(len(cands)), key=lambda i: -c[i])[:K]; l = lm_scorer(ctx, [cands[i] for i in idx])
        z = sum(c[i] for i in idx); o = [-1.0] * len(cands)
        for r, i in enumerate(idx): o[i] = W * c[i] / z + (1 - W) * l[r]
        return o
    r = {}
    for nm, sc, pl in (("A", inf_shipped_scorer(e, pool), pool), ("E+COV", cpu, xp), ("I", inter, xp)):
        s_, per, h = run_stream(test, sc, pl); r[nm] = s_; r[nm + "_top5"] = h[5]; pooled[nm].append(per)
    r["n_test"] = len(test); out["folds"].append(r)
    print(lang, f, {k: round(v, 2) for k, v in r.items()}, "elapsed", round(time.time() - t0), "s", flush=True)
    json.dump(out, open(f"results/cv_lm_{lang}.json", "w"), indent=1)
for k in ("A", "E+COV", "I"):
    v = [r[k] for r in out["folds"]]; out[k] = {"mean": st.mean(v), "sd": st.stdev(v)}
for a, b in (("A", "I"), ("A", "E+COV"), ("E+COV", "I")):
    d = [r[b] - r[a] for r in out["folds"]]; out[f"{b}_minus_{a}"] = {"mean": st.mean(d), "sd": st.stdev(d), "folds_positive": sum(x > 0 for x in d), "folds": [round(x, 2) for x in d]}
    pa = [p for fold in pooled[a] for p in fold]; pb = [p for fold in pooled[b] for p in fold]
    out[f"{b}_minus_{a}"]["pooled_95ci_pp"] = [round(x, 2) for x in boot_ci(pa, pb)]
out["seconds"] = time.time() - t0; json.dump(out, open(f"results/cv_lm_{lang}.json", "w"), indent=1)
