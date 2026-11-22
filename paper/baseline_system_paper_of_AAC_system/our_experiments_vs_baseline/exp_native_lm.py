"""Step 10b (GPU): does adding NATIVE Marathi/Gujarati text help the adapted LM?  Two-stage LoRA on BLOOM-560m:
   stage 1  native web/news sentences (data_native/<lang>_native_train.txt, 1 epoch, best checkpoint by native-dev char-ppl)
   stage 2  our AAC train split (same recipe as before; epoch picked by AAC dev char-ppl)
Compared on (i) AAC full-test char-ppl, (ii) native held-out char-ppl (out-of-domain), (iii) KSR of system I (E+COV top-10 + LM, w_cpu=0.1) on the FULL AAC test sets,
for: pretrained BLOOM | AAC-only adapter (existing results/lora_<lang>.pt) | native-only (after stage 1) | native -> AAC (stage 2).   python exp_native_lm.py <lang> [max_native_sentences]"""
import sys, os, json, math, random, time, torch, torch.nn as nn
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
from lib import *
from exp_improve_lib import softnorm
from exp_final import capped_scorer, mix, run_stream, boot_ci
from transformers import AutoTokenizer, AutoModelForCausalLM
lang = sys.argv[1]; NMAX = int(sys.argv[2]) if len(sys.argv) > 2 else 120000; K = 10
random.seed(0); torch.manual_seed(0); t00 = time.time()
rd = lambda p: [l.strip() for l in open(p, encoding="utf-8") if l.strip()]
nat_tr = rd(f"data_native/{lang}_native_train.txt"); nat_tr = random.Random(1).sample(nat_tr, min(NMAX, len(nat_tr))); nat_dev = rd(f"data_native/{lang}_native_dev.txt")[:600]; nat_te = rd(f"data_native/{lang}_native_test.txt")[:1500]
train = sents(lang, "train"); dev = sents(lang, "dev"); full = {k: sents(lang, "test", (k,)) for k in ("aac", "care")}; aac_te = full["aac"] + full["care"]
name = "bigscience/bloom-560m"; tok = AutoTokenizer.from_pretrained(name); BOS = tok.bos_token_id if tok.bos_token_id is not None else tok.eos_token_id
m = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float16).cuda(); m.requires_grad_(False); LORA_ON = [False]; LORAS = []
class LoRA(nn.Module):
    def __init__(self, base, r=16, alpha=32):
        super().__init__(); self.base = base; self.A = nn.Parameter(torch.randn(base.in_features, r, device="cuda") * 0.01); self.B = nn.Parameter(torch.zeros(r, base.out_features, device="cuda")); self.s = alpha / r
    def reset(self):
        with torch.no_grad(): self.A.normal_(0, 0.01); self.B.zero_()
    def forward(self, x):
        y = self.base(x)
        return y + ((x.float() @ self.A) @ self.B * self.s).to(y.dtype) if LORA_ON[0] else y
for mod in list(m.modules()):
    for nm_, ch in list(mod.named_children()):
        if nm_ in ("query_key_value", "dense", "dense_h_to_4h", "dense_4h_to_h") and isinstance(ch, nn.Linear): l_ = LoRA(ch); setattr(mod, nm_, l_); LORAS.append(l_)
params = [p for p in m.parameters() if p.requires_grad]
def enc_ids(ids):
    L = max(map(len, ids)); x = torch.full((len(ids), L), tok.pad_token_id); a = torch.zeros((len(ids), L), dtype=torch.long)
    for i, s in enumerate(ids): x[i, :len(s)] = torch.tensor(s); a[i, :len(s)] = 1
    return x.cuda(), a.cuda()
def tokenize(texts): return [[BOS] + t for t in tok(texts, add_special_tokens=False)["input_ids"]]   # batch call (Rust tokenizer, multi-threaded)
def seq_logp(texts, bs=8):
    out = []; ids = tokenize(texts)
    with torch.no_grad():
        for i in range(0, len(ids), bs):
            x, a = enc_ids(ids[i:i+bs]); lg = m(input_ids=x, attention_mask=a).logits[:, :-1].float()
            out += (torch.log_softmax(lg, -1).gather(-1, x[:, 1:, None])[..., 0] * a[:, 1:]).sum(1).tolist()
    return out
def cppl(texts): return math.exp(-sum(seq_logp(texts)) / sum(len(t) for t in texts))
def train_epoch(texts, opt, scaler, log_every=None, evalfn=None):
    d = texts[:]; random.shuffle(d); ids = tokenize(d); m.train(); best = None
    for i in range(0, len(ids), 16):
        for j in range(i, min(i + 16, len(ids)), 4):
            x, a = enc_ids(ids[j:j+4]); lg = m(input_ids=x, attention_mask=a).logits[:, :-1].float()
            scaler.scale(nn.functional.cross_entropy(lg.reshape(-1, lg.shape[-1]), x[:, 1:].reshape(-1), ignore_index=tok.pad_token_id) / 4).backward()
        scaler.step(opt); scaler.update(); opt.zero_grad()
        if log_every and (i // 16 + 1) % log_every == 0:
            m.eval(); v = evalfn(); m.train(); print(f"  step {i//16+1}/{len(ids)//16} native-dev char-ppl {v:.3f}  elapsed {time.time()-t00:.0f}s", flush=True)
            if best is None or v < best[0]: best = (v, {k: t.clone() for k, t in m.state_dict().items() if ".A" in k or ".B" in k}, i // 16 + 1)
    m.eval(); return best
def adapter_state(): return {k: t.clone() for k, t in m.state_dict().items() if ".A" in k or ".B" in k}

res = {"lang": lang, "n_native_train": len(nat_tr), "n_native_dev": len(nat_dev), "n_native_test": len(nat_te), "n_aac_train": len(train), "ppl": {}}
def measure(tag):
    m.eval(); res["ppl"][tag] = {"aac_test": cppl(aac_te), "native_test": cppl(nat_te)}; print(tag, res["ppl"][tag], flush=True); json.dump(res, open(f"results/native_{lang}.json", "w"), indent=1)
LORA_ON[0] = False; measure("pretrained")
LORA_ON[0] = True; m.load_state_dict(torch.load(f"results/lora_{lang}.pt"), strict=False); measure("AAC-only (existing adapter)"); aac_only = adapter_state()
# ---- stage 1: native text
for l_ in LORAS: l_.reset()
opt = torch.optim.AdamW(params, lr=2e-4, weight_decay=0.0); scaler = torch.amp.GradScaler("cuda")
t1 = time.time(); best = train_epoch(nat_tr, opt, scaler, log_every=max(len(nat_tr) // 16 // 4, 1), evalfn=lambda: cppl(nat_dev))
m.load_state_dict(best[1], strict=False); res["stage1"] = {"best_step": best[2], "native_dev_ppl": best[0], "seconds": time.time() - t1}; measure("native-only (stage 1)"); native_only = adapter_state()
# ---- stage 2: AAC text on top
best2 = (1e9, None, 0)
for ep in range(1, 4):
    train_epoch(train, opt, scaler); dp = cppl(dev); print("stage2 epoch", ep, "AAC dev char-ppl", round(dp, 3), flush=True)
    if dp < best2[0]: best2 = (dp, adapter_state(), ep)
m.load_state_dict(best2[1], strict=False); torch.save(best2[1], f"results/lora_native_{lang}.pt"); res["stage2"] = {"best_epoch": best2[2], "aac_dev_ppl": best2[0]}; measure("native -> AAC (stage 2)"); both = best2[1]
# ---- KSR of system I with each adapter (K=10, FULL test sets)
cm = CharNgram(12).train(train); e = make_engine(train, lang); pool = Pool(train, 300); tuned = json.load(open(f"results/final_{lang}.json"))[lang]["tuned"]
C, a_ = tuned["step1+5 ctx_cap,alpha"]; wch = tuned["step2 mix_weight_infgram"]; W = json.load(open(f"results/step5_{lang}.json"))["chosen_cpu_weight"]
src = open("exp_step4.py").read(); exec(src[src.index("class ExtPool"):src.index("def es(base")]); xp = ExtPool(pool, cm, M=5)
chs = lambda ctx, cands, g=charlm_scorer(cm): softnorm(g(ctx, cands)); cpu = mix(capped_scorer(e, C, a_), chs, wch); cache = {}
@torch.no_grad()
def lm_scorer(ctx, cands):
    sc = cache.setdefault(tuple(ctx), {}); miss = [w for w in cands if w not in sc]; text = " ".join(ctx); base_ids = [BOS] + (tok(text, add_special_tokens=False)["input_ids"] if text else [])
    if miss:
        ws = [tok((" " if ctx else "") + w, add_special_tokens=False)["input_ids"] for w in miss]; L = len(base_ids) + max(map(len, ws))
        ids = torch.full((len(miss), L), tok.pad_token_id); att = torch.zeros((len(miss), L), dtype=torch.long)
        for j, w in enumerate(ws): s_ = base_ids + w; ids[j, :len(s_)] = torch.tensor(s_); att[j, :len(s_)] = 1
        h = m.transformer(input_ids=ids.cuda(), attention_mask=att.cuda()).last_hidden_state[:, len(base_ids)-1:]; lp = torch.log_softmax(m.lm_head(h).float(), -1)
        for j, w in enumerate(ws): sc[miss[j]] = sum(lp[j, k, t].item() for k, t in enumerate(w))
    return softnorm([sc[w] for w in cands])
def inter(ctx, cands):
    c = cpu(ctx, cands); idx = sorted(range(len(cands)), key=lambda i: -c[i])[:K]; l = lm_scorer(ctx, [cands[i] for i in idx]); z = sum(c[i] for i in idx); o = [-1.0] * len(cands)
    for r, i in enumerate(idx): o[i] = W * c[i] / z + (1 - W) * l[r]
    return o
res["ksr_K10_full_test"] = {}; per = {}
for tag, st_ in (("AAC-only", aac_only), ("native-only", native_only), ("native -> AAC", both)):
    m.load_state_dict(st_, strict=False); cache.clear(); r = {}; per[tag] = {}
    for k, v in full.items(): s_, p, h = run_stream(v, inter, xp); r[k] = dict(ksr_pct=s_, top5=h[5]); per[tag][k] = p
    r["avg_ksr"] = (r["aac"]["ksr_pct"] + r["care"]["ksr_pct"]) / 2; r["avg_top5"] = (r["aac"]["top5"] + r["care"]["top5"]) / 2; res["ksr_K10_full_test"][tag] = r
    print(lang, tag, "KSR", round(r["avg_ksr"], 2), "top5", round(r["avg_top5"], 1), round(time.time() - t00), "s", flush=True); json.dump(res, open(f"results/native_{lang}.json", "w"), indent=1)
for tag in ("native-only", "native -> AAC"):
    res["ksr_K10_full_test"][tag]["gain_vs_AAC-only_95ci_pp"] = {k: [round(x, 2) for x in boot_ci(per["AAC-only"][k], per[tag][k])] for k in full}
res["seconds"] = time.time() - t00; json.dump(res, open(f"results/native_{lang}.json", "w"), indent=1)
