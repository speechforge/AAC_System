"""Step 2: adapt a multilingual LM (BLOOM-560m, LoRA) on the language's AAC train text and use it as the next-word ranker.
Controls: shipped CPU engine (A), improved CPU stack (E), pretrained BLOOM (zero-shot), adapted BLOOM, CPU stack + adapted BLOOM hybrid.
All knobs (epochs, mix weight) chosen on DEV. Test = random N+N test sentences (same sample for every system) + per-character perplexity on the FULL test set.
   python exp_step2.py <lang> [N]"""
import sys, json, math, random, time, torch, torch.nn as nn
from lib import *
from exp_improve_lib import softnorm
from exp_final import capped_scorer, mix, run_stream, boot_ci
from transformers import AutoTokenizer, AutoModelForCausalLM
lang = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 100
random.seed(0); torch.manual_seed(0)
train = sents(lang, "train"); dev = sents(lang, "dev"); full = {k: sents(lang, "test", (k,)) for k in ("aac", "care")}
sub = {k: random.Random(1).sample(v, min(N, len(v))) for k, v in full.items()}
name = "bigscience/bloom-560m"; tok = AutoTokenizer.from_pretrained(name); BOS = tok.bos_token_id if tok.bos_token_id is not None else tok.eos_token_id
m = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float16).cuda(); m.requires_grad_(False)
LORA_ON = [False]
class LoRA(nn.Module):
    def __init__(self, base, r=16, alpha=32):
        super().__init__(); self.base = base; self.A = nn.Parameter(torch.randn(base.in_features, r, device="cuda") * 0.01); self.B = nn.Parameter(torch.zeros(r, base.out_features, device="cuda")); self.s = alpha / r
    def forward(self, x):
        y = self.base(x)
        return y + ((x.float() @ self.A) @ self.B * self.s).to(y.dtype) if LORA_ON[0] else y
n_l = 0
for mod in list(m.modules()):
    for nm_, ch in list(mod.named_children()):
        if nm_ in ("query_key_value", "dense", "dense_h_to_4h", "dense_4h_to_h") and isinstance(ch, nn.Linear): setattr(mod, nm_, LoRA(ch)); n_l += 1
params = [p for p in m.parameters() if p.requires_grad]; print("lora layers", n_l, "trainable", sum(p.numel() for p in params), flush=True)

def enc_batch(texts):
    ids = [[BOS] + tok(t, add_special_tokens=False)["input_ids"] for t in texts]; L = max(map(len, ids))
    x = torch.full((len(ids), L), tok.pad_token_id); a = torch.zeros((len(ids), L), dtype=torch.long)
    for i, s in enumerate(ids): x[i, :len(s)] = torch.tensor(s); a[i, :len(s)] = 1
    return x.cuda(), a.cuda()
def seq_logp(texts, bs=4):          # per-sentence natural-log prob of all tokens after BOS
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), bs):
            x, a = enc_batch(texts[i:i+bs]); lg = m(input_ids=x, attention_mask=a).logits[:, :-1].float()
            lp = torch.log_softmax(lg, -1).gather(-1, x[:, 1:, None])[..., 0] * a[:, 1:]; out += lp.sum(1).tolist()
    return out
def char_ppl_lm(texts):
    lp = seq_logp(texts); n = sum(len(t) for t in texts); return math.exp(-sum(lp) / n)

cache = {}
@torch.no_grad()
def lm_scorer(ctx, cands):
    key = (LORA_ON[0], tuple(ctx)); sc = cache.setdefault(key, {}); miss = [w for w in cands if w not in sc]
    text = " ".join(ctx); base_ids = [BOS] + (tok(text, add_special_tokens=False)["input_ids"] if text else [])
    for i in range(0, len(miss), 48):
        ch = miss[i:i+48]; ws = [tok((" " if ctx else "") + w, add_special_tokens=False)["input_ids"] for w in ch]
        L = len(base_ids) + max(map(len, ws)); ids = torch.full((len(ch), L), tok.pad_token_id); att = torch.zeros((len(ch), L), dtype=torch.long)
        for j, w in enumerate(ws): s_ = base_ids + w; ids[j, :len(s_)] = torch.tensor(s_); att[j, :len(s_)] = 1
        h = m.transformer(input_ids=ids.cuda(), attention_mask=att.cuda()).last_hidden_state[:, len(base_ids)-1:]
        lp = torch.log_softmax(m.lm_head(h).float(), -1)
        for j, w in enumerate(ws): sc[ch[j]] = sum(lp[j, k, t].item() for k, t in enumerate(w))
    return softnorm([sc[w] for w in cands])

res = {"lang": lang, "model": name, "n_per_set": N, "lora_trainable_params": sum(p.numel() for p in params)}
cm = CharNgram(12).train(train)
# --- perplexity of pretrained (zero-shot) on full test
t0 = time.time(); allt = full["aac"] + full["care"]
res["char_ppl"] = {"char12": char_ppl(lambda s: cm.logp_str("", s), allt)[0]}
LORA_ON[0] = False; res["char_ppl"]["bloom_pretrained"] = char_ppl_lm(allt); print("ppl pretrained", res["char_ppl"], flush=True)
# --- adapt (LoRA), early stopping on dev loss
LORA_ON[0] = True; opt = torch.optim.AdamW(params, lr=2e-4, weight_decay=0.0); scaler = torch.cuda.amp.GradScaler()
best = (1e9, None, 0); hist = []
for ep in range(1, 4):
    d = train[:]; random.shuffle(d); m.train()
    for i in range(0, len(d), 16):                       # effective batch 16 = 4 micro-batches of 4 (250k-vocab logits are large)
        for j in range(i, min(i + 16, len(d)), 4):
            x, a = enc_batch(d[j:j+4]); lg = m(input_ids=x, attention_mask=a).logits[:, :-1].float()
            loss = nn.functional.cross_entropy(lg.reshape(-1, lg.shape[-1]), x[:, 1:].reshape(-1), ignore_index=tok.pad_token_id) / 4
            scaler.scale(loss).backward()
        scaler.step(opt); scaler.update(); opt.zero_grad()
    m.eval(); dp = char_ppl_lm(dev); hist.append(dp); print("epoch", ep, "dev char-ppl", round(dp, 3), round(time.time() - t0), "s", flush=True)
    if dp < best[0]: best = (dp, {k: v.clone() for k, v in m.state_dict().items() if ".A" in k or ".B" in k}, ep)
m.load_state_dict(best[1], strict=False); res["dev_ppl_by_epoch"] = hist; res["best_epoch"] = best[2]
res["char_ppl"]["bloom_adapted"] = char_ppl_lm(allt); res["char_ppl"]["bloom_adapted_dev"] = best[0]; print("ppl", res["char_ppl"], flush=True)
# --- KSR / top-k
e = make_engine(train, lang); pool = Pool(train, 300); tuned = json.load(open(f"results/final_{lang}.json"))[lang]["tuned"]
C, a_ = tuned["step1+5 ctx_cap,alpha"]; wch = tuned["step2 mix_weight_infgram"]
chs = lambda ctx, cands, f=charlm_scorer(cm): softnorm(f(ctx, cands))
cpu = mix(capped_scorer(e, C, a_), chs, wch)
def pretrained(ctx, cands):
    LORA_ON[0] = False
    try: return lm_scorer(ctx, cands)
    finally: LORA_ON[0] = True
bw = (-1, None); D = dev[:60]
for w in (0.0, 0.1, 0.2, 0.3, 0.5):
    s = run_stream(D, mix(cpu, lm_scorer, w) if w > 0 else lm_scorer, pool)[0]; print("dev w_cpu", w, round(s, 2), flush=True)
    if s > bw[0]: bw = (s, w)
w = bw[1]; res["weight_on_cpu_stack"] = w; res["dev_ksr_60"] = bw[0]; res["systems"] = {}; per = {}
systems = [("A shipped infinity-gram", inf_shipped_scorer(e, pool)), ("E improved CPU stack (no personalisation)", cpu), ("BLOOM-560m pretrained (zero-shot)", pretrained),
           ("BLOOM-560m adapted (LoRA)", lm_scorer), ("G CPU stack + adapted BLOOM", mix(cpu, lm_scorer, w) if w > 0 else lm_scorer)]
for nm, sc in systems:
    r = {}; per[nm] = {}
    for k, v in sub.items():
        s, p, h = run_stream(v, sc, pool); r[k] = dict(ksr_pct=s, top1=h[1], top3=h[3], top5=h[5], top10=h[10]); per[nm][k] = p
    r["avg_ksr"] = (r["aac"]["ksr_pct"] + r["care"]["ksr_pct"]) / 2; res["systems"][nm] = r; print(lang, nm, round(r["avg_ksr"], 2), round((r["aac"]["top5"] + r["care"]["top5"]) / 2, 1), round(time.time() - t0), "s", flush=True)
    json.dump(res, open(f"results/step2_{lang}.json", "w"), indent=1)
for nm in list(res["systems"])[1:]:
    res["systems"][nm]["gain_vs_shipped_95ci_pp"] = {k: [round(x, 2) for x in boot_ci(per[systems[0][0]][k], per[nm][k])] for k in sub}
res["seconds"] = time.time() - t0; json.dump(res, open(f"results/step2_{lang}.json", "w"), indent=1)
