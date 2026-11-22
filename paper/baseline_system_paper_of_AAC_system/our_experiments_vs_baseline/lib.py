"""Shared evaluation code: text normalisation, char n-gram baseline, word-level scorers, KSR simulator."""
import json, os, re, math, sys, time, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while ROOT != "/" and not os.path.isdir(os.path.join(ROOT, "indic-generative-aac")):   # repo root, works from either folder location
    ROOT = os.path.dirname(ROOT)
D = os.path.join(HERE, "data")
sys.path.insert(0, os.path.join(ROOT, "indic-generative-aac", "backend"))

SCRIPT = {"en": r"[a-z']+", "hi": r"[ऀ-ॣ०-ॿ]+", "mr": r"[ऀ-ॣ०-ॿ]+", "gu": r"[઀-૰૱-૿]+"}

def words_of(text, lang):
    t = text.lower() if lang == "en" else text
    if lang == "en": t = t.replace("’", "'")
    return re.findall(SCRIPT[lang], t)

def norm(text, lang):
    return " ".join(words_of(text, lang))

def load(lang, split, role):
    p = f"{D}/{lang}_{split}_{role}.json"
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []

def sents(lang, split, roles=("aac", "care")):
    out = []
    for r in roles:
        for s in load(lang, split, r):
            n = norm(s, lang)
            if lang in ("mr", "gu") and n:      # machine-translated data: drop degenerate NLLB repetition loops / runaway output
                w = n.split()
                if len(w) > 30 or max(collections.Counter(w).values()) >= 4: continue
            if n: out.append(n)
    return out

# ───────────────────────── character n-gram (Witten-Bell interpolation), the "AAC n-gram" analogue ─────────────────────────
class CharNgram:
    def __init__(self, order=12):
        self.n = order; self.cnt = collections.defaultdict(collections.Counter); self.alpha = set()
        self.memo = {}
    def train(self, sentences):
        for s in sentences:
            t = "^" * (self.n - 1) + s
            for i in range(self.n - 1, len(t)):
                c = t[i]; self.alpha.add(c)
                for k in range(0, self.n):
                    self.cnt[t[i - k:i]][c] += 1
        self.alpha.add(" ")
        self.V = len(self.alpha) + 1       # +1 reserves mass for unseen symbols
        self.tot = {h: sum(c.values()) for h, c in self.cnt.items()}
        self.typ = {h: len(c) for h, c in self.cnt.items()}
        return self
    def p(self, hist, c):
        h = ("^" * (self.n - 1) + hist)[-(self.n - 1):] if self.n > 1 else ""
        key = (h, c)
        r = self.memo.get(key)
        if r is not None: return r
        pr = 1.0 / self.V
        for k in range(0, self.n):
            ctx = h[len(h) - k:] if k else ""
            T = self.tot.get(ctx)
            if not T: break
            ty = self.typ[ctx]; lam = T / (T + ty)
            pr = lam * (self.cnt[ctx].get(c, 0) / T) + (1 - lam) * pr
        self.memo[key] = pr
        return pr
    def logp_str(self, hist, s):
        lp = 0.0
        for i, c in enumerate(s):
            lp += math.log(self.p(hist + s[:i], c))
        return lp
    def norm_p(self, hist, c, syms):
        z = sum(self.p(hist, x) for x in syms)
        return self.p(hist, c) / z

def char_ppl(model_logp_fn, sentences):
    """model_logp_fn(sentence)-> total natural-log prob of the sentence's characters. per-char ppl incl. spaces."""
    nll, n = 0.0, 0
    for s in sentences:
        nll -= model_logp_fn(s); n += len(s)
    return math.exp(nll / max(n, 1)), n

# ───────────────────────── keystroke-savings simulator (paper protocol, 5 predictions) ─────────────────────────
def ksr(sentences, predict, n_pred=5):
    """predict(context_words, prefix)->ranked list of words. Returns (ksr%, ka, kp, hit_at_empty_prefix dict)."""
    ka = kp = 0; empty_hits = collections.Counter(); nwords = 0
    for s in sentences:
        ws = s.split()
        for i, w in enumerate(ws):
            ka += len(w) + 1
            best = len(w) + 1
            for k in range(0, len(w)):           # k chars typed, prediction shown
                preds = predict(ws[:i], w[:k])[:n_pred]
                if k == 0:
                    top10 = predict(ws[:i], "")[:10]
                    for K in (1, 3, 5, 10):
                        if w in top10[:K]: empty_hits[K] += 1
                    nwords += 1
                if w in preds:
                    best = k + 1; break
            kp += best
    return 100.0 * (ka - kp) / ka, ka, kp, {K: 100.0 * empty_hits[K] / max(nwords, 1) for K in (1, 3, 5, 10)}, nwords

class Pool:
    """Candidate pool shared by every system: train-vocabulary, top-N most frequent words matching the typed prefix."""
    def __init__(self, train_sents, N=300):
        self.freq = collections.Counter(w for s in train_sents for w in s.split())
        self.ranked = [w for w, _ in self.freq.most_common()]; self.N = N
        self.cache = {}
    def get(self, prefix):
        r = self.cache.get(prefix)
        if r is None:
            r = [w for w in self.ranked if w.startswith(prefix)][: self.N]
            self.cache[prefix] = r
        return r

def predictor_from_scorer(score_fn, pool, memo=True):
    """score_fn(context_words, candidate_words)->list of scores (higher better)."""
    cache = {}
    def predict(ctx, prefix):
        cands = pool.get(prefix)
        if not cands: return []
        key = (tuple(ctx), prefix)
        if key not in cache:
            sc = score_fn(list(ctx), cands)
            cache[key] = [w for _, w in sorted(zip(sc, cands), key=lambda x: -x[0])]
        return cache[key]
    return predict

def charlm_scorer(cm):
    def score(ctx, cands):
        hist = " ".join(ctx) + (" " if ctx else "")
        return [cm.logp_str(hist, w + " ") for w in cands]
    return score

# ───────────────────────── ∞-gram (our engine) ─────────────────────────
import tempfile
def make_engine(train_sents, lang):
    import infinity_gram as IG
    e = IG.AACInfinityGramEngine(data_root=tempfile.mkdtemp())          # empty data root -> only seeds are loaded
    e.root_en, e.root_hi = IG.InfinityGramNode(), IG.InfinityGramNode()
    e.unigrams_en.clear(); e.unigrams_hi.clear(); e.start_priors_en.clear(); e.start_priors_hi.clear()
    e.vocab_en.clear(); e.vocab_hi.clear(); e.sentence_count = e.total_tokens = e.max_depth_seen = 0
    tag = "hi" if lang in ("hi", "mr") else "en"          # gu is not Devanagari: routed to the generic root (no lowercasing effect)
    for s in train_sents: e.add_sentence(s.split(), tag)
    e.tag = tag
    return e

def inf_shipped_scorer(e, pool):
    """Exactly the shipped predict_next (incl. its exclusion of already-selected words)."""
    uni = e.unigrams_hi if e.tag == "hi" else e.unigrams_en
    tot = sum(uni.values())
    def score(ctx, cands):
        d = {r["word"]: r["prob"] for r in e.predict_next(ctx, language=e.tag, top_k=100000)}
        return [d.get(w, 0.0) + 1e-6 * uni.get(w, 0) / tot for w in cands]
    return score

def inf_dist(e, ctx, backoff=0.4):
    """Normalised ∞-gram word distribution WITHOUT the already-selected exclusion (a proper LM for perplexity)."""
    root = e.root_hi if e.tag == "hi" else e.root_en
    cand = collections.defaultdict(float); weight = 1.0
    for st in range(len(ctx)):
        node = root; ok = True
        for w in ctx[st:]:
            node = node.children.get(w)
            if node is None: ok = False; break
        if ok and node.children:
            tt = sum(c.count for c in node.children.values())
            for w, c in node.children.items(): cand[w] += c.count / tt * weight
        weight *= backoff
    if not ctx:
        sp = e.start_priors_hi if e.tag == "hi" else e.start_priors_en
        t = sum(sp.values()) or 1
        for w, c in sp.items(): cand[w] += c / t
    z = sum(cand.values()) or 1.0
    return {w: v / z for w, v in cand.items()}

def inf_logp_fn(e, cm, mu=0.1, eps=0.1):
    uni = e.unigrams_hi if e.tag == "hi" else e.unigrams_en
    T = sum(uni.values())
    def logp(s):
        ws = s.split(); lp = 0.0
        for i, w in enumerate(ws):
            d = inf_dist(e, ws[:i])
            pv = (1 - mu) * d.get(w, 0.0) + mu * uni.get(w, 0) / T
            hist = " ".join(ws[:i]) + (" " if i else "")
            lpc = cm.logp_str(hist, w + (" " if i < len(ws) - 1 else "")) + math.log(eps)
            a = math.log((1 - eps) * pv) if pv > 0 else -1e9
            m_ = max(a, lpc); lp += m_ + math.log(math.exp(a - m_) + math.exp(lpc - m_))
        return lp
    return logp
