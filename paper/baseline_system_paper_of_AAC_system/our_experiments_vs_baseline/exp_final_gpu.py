"""Step 3 at larger scale (English): improved CPU stack + in-domain adapted OPT-125m re-ranker. 100+100 test sentences, weight tuned on 60 dev sentences."""
import sys, json, random, torch
from lib import *
from exp_improve_lib import softnorm
from exp_final import capped_scorer, mix, run_stream, boot_ci
random.seed(0); lang = "en"
train = sents(lang, "train"); dev = sents(lang, "dev")
full = {"aac": sents(lang, "test", ("aac",)), "care": sents(lang, "test", ("care",))}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
sub = {k: random.Random(1).sample(v, min(N, len(v))) for k, v in full.items()}
from transformers import AutoTokenizer, AutoModelForCausalLM
name = "facebook/opt-125m"; tok = AutoTokenizer.from_pretrained(name); m = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float32).cuda()
opt = torch.optim.AdamW(m.parameters(), lr=3e-5, weight_decay=0.01); m.train()
d = train[:]; random.shuffle(d)
for i in range(0, len(d), 16):
    enc = tok(d[i:i+16], return_tensors="pt", padding=True); lab = enc["input_ids"].clone(); lab[enc["attention_mask"] == 0] = -100
    m(**enc.to("cuda"), labels=lab.cuda()).loss.backward(); opt.step(); opt.zero_grad()
m.half().eval(); cache = {}
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
e = make_engine(train, lang); pool = Pool(train, 300); cm = CharNgram(12).train(train)
chs = lambda ctx, cands, f=charlm_scorer(cm): softnorm(f(ctx, cands))
capd = capped_scorer(e, 3, 0.2); cpu_best = mix(capd, chs, 0.85)           # CPU stack tuned in exp_final.py
best = (-1, None); D = dev[:60]
for w in (0.0, 0.1, 0.2, 0.3, 0.5):      # weight on the CPU stack (0 = LM alone)
    s = run_stream(D, mix(cpu_best, opt_scorer, w), pool)[0] if w > 0 else run_stream(D, opt_scorer, pool)[0]
    print("dev w", w, round(s, 2), flush=True)
    if s > best[0]: best = (s, w)
w = best[1]; res = {"weight_on_cpu_stack": w, "dev_ksr_60": best[0], "n_per_set": N, "systems": {}}; per = {}
systems = [("A shipped infinity-gram", inf_shipped_scorer(e, pool)), ("E' improved CPU stack (step1+5+2)", cpu_best), ("adapted OPT-125m alone", opt_scorer),
           ("F step1+5+2+3: CPU stack + adapted OPT-125m", mix(cpu_best, opt_scorer, w) if w > 0 else opt_scorer)]
for nm, sc in systems:
    r = {}; per[nm] = {}
    for k, v in sub.items():
        s, p, h = run_stream(v, sc, pool); r[k] = dict(ksr_pct=s, top1=h[1], top3=h[3], top5=h[5], top10=h[10]); per[nm][k] = p
    r["avg_ksr"] = (r["aac"]["ksr_pct"] + r["care"]["ksr_pct"]) / 2; res["systems"][nm] = r; print(nm, round(r["avg_ksr"], 2), flush=True)
    json.dump({"en": res}, open("results/final_gpu_en.json", "w"), indent=1)
for nm in list(res["systems"])[1:]:
    res["systems"][nm]["gain_vs_shipped_95ci_pp"] = {k: [round(x, 2) for x in boot_ci(per[systems[0][0]][k], per[nm][k])] for k in sub}
json.dump({"en": res}, open("results/final_gpu_en.json", "w"), indent=1)
