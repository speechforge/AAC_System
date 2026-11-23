"""
predictor_v2.py - improved CPU next-word / word-completion predictor (en, hi, mr, gu), no GPU needed.

Measured against the shipped infinity_gram.py predictor in paper/baseline_system_paper_of_AAC_system/20_nov_changes.md
(KSR, higher is better; full test sets, mean of AAC+caregiver):  en 56.29 -> 57.49,  hi 56.74 -> 58.28,
mr 48.73 -> 51.86,  gu 53.04 -> 55.60.

What it adds over the shipped predictor
  1. One model per language (the shipped engine sends Gujarati to the English trie and Marathi to the Hindi trie).
  2. Already-selected words are NOT excluded (a repeated word such as "to ... to" is legitimate); callers dedupe if they want.
  3. Context is capped (per language, tuned on dev) before the infinity-gram back-off.
  4. Word distribution = w * infinity-gram + (1 - w) * character 12-gram (Witten-Bell), tuned on dev.
  5. Coverage fallback: when a typed prefix of >= 2 characters is given, up to 5 character-12-gram beam-search completions that
     are NOT in the training vocabulary join the candidate pool (words never seen in training).

Public API:  predict(words, language, prefix="", top_k=10) -> list of {"word","prob","emoji","order","order_label","source"}
The module is import-safe: nothing is trained until the first request for a language (lazy, thread-safe).
"""
import collections
import json
import math
import os
import re
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "predictor_data")

# Knobs tuned on DEV only (paper/.../our_experiments_vs_baseline/results/final_<lang>.json, step4_<lang>.json).
PARAMS = {
    "en": {"ctx_cap": 3, "backoff": 0.2, "w_inf": 0.85},
    "hi": {"ctx_cap": 4, "backoff": 0.2, "w_inf": 0.70},
    "mr": {"ctx_cap": 2, "backoff": 0.2, "w_inf": 0.70},
    "gu": {"ctx_cap": 2, "backoff": 0.6, "w_inf": 0.70},
}
POOL_N = 300          # candidate pool: most frequent training words that match the typed prefix
COV_M = 5             # extra out-of-vocabulary completions
COV_MINLEN = 2        # only when at least this many characters were typed
COV_WIDTH, COV_STEPS = 8, 10

SCRIPT = {"en": r"[a-z']+", "hi": r"[ऀ-ॣ०-ॿ]+", "mr": r"[ऀ-ॣ०-ॿ]+", "gu": r"[઀-૰૱-૿]+"}
LANGS = tuple(SCRIPT)


def words_of(text, lang):
    t = text.lower() if lang == "en" else text
    if lang == "en":
        t = t.replace("’", "'")
    return re.findall(SCRIPT[lang], t)


class CharNgram:
    """Character n-gram, Witten-Bell interpolation."""

    def __init__(self, order=12):
        self.n = order
        self.cnt = collections.defaultdict(collections.Counter)
        self.alpha = set()
        self.memo = {}

    def train(self, sentences):
        for s in sentences:
            t = "^" * (self.n - 1) + s
            for i in range(self.n - 1, len(t)):
                c = t[i]
                self.alpha.add(c)
                for k in range(0, self.n):
                    self.cnt[t[i - k:i]][c] += 1
        self.alpha.add(" ")
        self.V = len(self.alpha) + 1
        self.tot = {h: sum(c.values()) for h, c in self.cnt.items()}
        self.typ = {h: len(c) for h, c in self.cnt.items()}
        return self

    def p(self, hist, c):
        h = ("^" * (self.n - 1) + hist)[-(self.n - 1):] if self.n > 1 else ""
        key = (h, c)
        r = self.memo.get(key)
        if r is not None:
            return r
        pr = 1.0 / self.V
        for k in range(0, self.n):
            ctx = h[len(h) - k:] if k else ""
            T = self.tot.get(ctx)
            if not T:
                break
            lam = T / (T + self.typ[ctx])
            pr = lam * (self.cnt[ctx].get(c, 0) / T) + (1 - lam) * pr
        if len(self.memo) > 400000:        # bounded cache for a long-running server
            self.memo.clear()
        self.memo[key] = pr
        return pr

    def logp_str(self, hist, s):
        lp = 0.0
        for i, c in enumerate(s):
            lp += math.log(self.p(hist + s[:i], c))
        return lp


class _Node:
    __slots__ = ("count", "children")

    def __init__(self):
        self.count = 0
        self.children = {}


def _insert(root, start, ws):
    """Add one sentence to a suffix trie (every suffix, so the longest matching context can be found)."""
    start[ws[0]] += 1
    for i in range(len(ws)):
        node = root
        node.count += 1
        for w in ws[i:]:
            node = node.children.setdefault(w, _Node())
            node.count += 1


def _trie_dist(root, start, ctx, alpha):
    """Infinity-gram next-word distribution: every matching context suffix, longer ones weighted more (back-off alpha)."""
    cand = collections.defaultdict(float)
    weight = 1.0
    for st in range(len(ctx)):
        node = root
        for w in ctx[st:]:
            node = node.children.get(w)
            if node is None:
                break
        if node is not None and node.children:
            tt = sum(c.count for c in node.children.values())
            for w, c in node.children.items():
                cand[w] += c.count / tt * weight
        weight *= alpha
    if not ctx:
        t = sum(start.values()) or 1
        for w, c in start.items():
            cand[w] += c / t
    z = sum(cand.values()) or 1.0
    return {w: v / z for w, v in cand.items()}


def _index(idx, ws):
    """Sentence memory: words so far -> counts of how the sentence went on (only continuations of 2+ words)."""
    for i in range(len(ws) - 1):
        idx[tuple(ws[:i])][tuple(ws[i:])] += 1


class Personal:
    """One user's own sentences in one language (from their saved conversations and phrases): a small infinity-gram,
    word counts and a sentence memory. Built per request from at most ~200 sentences, so it costs about a millisecond."""

    def __init__(self, lang, sentences=()):
        self.lang = lang
        self.root, self.start, self.uni = _Node(), collections.Counter(), collections.Counter()
        self.idx = collections.defaultdict(collections.Counter)
        for s in sentences:
            self.add(s)

    def add(self, text):
        ws = words_of(text, self.lang) if isinstance(text, str) else list(text)
        if ws:
            _insert(self.root, self.start, ws)
            self.uni.update(ws)
            _index(self.idx, ws)

    def dist(self, ctx, prefix=""):
        """P(next word | context, typed letters) from this user's history only (0.7 infinity-gram + 0.3 word counts)."""
        if not self.uni:
            return {}
        tr = _trie_dist(self.root, self.start, ctx[-3:], 0.2)
        T = sum(self.uni.values())
        d = {w: 0.7 * tr.get(w, 0.0) + 0.3 * c / T for w, c in self.uni.items() if w.startswith(prefix)}
        z = sum(d.values())
        return {w: v / z for w, v in d.items()} if z else {}


LAM = {"en": 0.1, "hi": 0.1, "mr": 0.1, "gu": 0.1}   # weight of the personal model (best of 0.1-0.5 on dev in all 4 languages, Step 16)


def personalise(ranked, pm, ctx, prefix="", lam=0.1):
    """Mix the user's own model into a ranked [(score, word)] list. New words the user has used before join the list."""
    d = pm.dist(list(ctx), prefix) if pm is not None and lam > 0 else {}
    if not d:
        return ranked
    z = sum(s for s, _ in ranked) or 1.0
    sc = {w: (1 - lam) * s / z for s, w in ranked}
    for w, p in d.items():
        sc[w] = sc.get(w, 0.0) + lam * p
    return sorted(((s, w) for w, s in sc.items()), key=lambda x: -x[0])


def _softnorm(sc):
    m = max(sc)
    e = [math.exp(x - m) for x in sc]
    z = sum(e)
    return [x / z for x in e]


class LangModel:
    """Everything for one language, built from a list of normalised sentences (words joined by single spaces)."""

    def __init__(self, lang, sentences, params=None, cov=True):
        self.lang = lang
        self.params = dict(PARAMS[lang], **(params or {}))
        self.use_cov = cov
        self.root = _Node()
        self.uni = collections.Counter()
        self.start = collections.Counter()
        self.idx = collections.defaultdict(collections.Counter)    # sentence memory of the training text
        for s in sentences:
            ws = s.split()
            if not ws:
                continue
            self.uni.update(ws)
            _insert(self.root, self.start, ws)     # all suffixes -> longest-suffix lookup
            _index(self.idx, ws)
        self.T = sum(self.uni.values()) or 1
        self.cm = CharNgram(12).train(sentences)
        self.ranked = [w for w, _ in self.uni.most_common()]
        self._pool_cache, self._cand_cache = {}, {}
        self.n_sentences = len(sentences)

    # ---- candidates -------------------------------------------------------------------------------------------------------
    def pool(self, prefix):
        r = self._pool_cache.get(prefix)
        if r is None:
            r = [w for w in self.ranked if w.startswith(prefix)][:POOL_N]
            if len(self._pool_cache) > 5000:
                self._pool_cache.clear()
            self._pool_cache[prefix] = r
        return r

    def candidates(self, prefix):
        """Pool plus up to COV_M out-of-vocabulary completions found by char-12-gram beam search."""
        r = self._cand_cache.get(prefix)
        if r is not None:
            return r
        base = self.pool(prefix)
        r = list(base)
        if self.use_cov and len(prefix) >= COV_MINLEN and COV_M > 0:
            beams, done = [(0.0, prefix)], []
            for _ in range(COV_STEPS):
                nb = []
                for lp, w in beams:
                    for c in self.cm.alpha:
                        q = lp + math.log(self.cm.p(" " + w, c))
                        (done if c == " " else nb).append((q, w if c == " " else w + c))
                beams = sorted(nb, reverse=True)[:COV_WIDTH]
                if not beams:
                    break
            seen = set(r)
            for _, w in sorted(done, reverse=True):
                if w not in seen and w != prefix:
                    r.append(w)
                    seen.add(w)
                if len(r) >= len(base) + COV_M:
                    break
        if len(self._cand_cache) > 5000:
            self._cand_cache.clear()
        self._cand_cache[prefix] = r
        return r

    # ---- scoring ----------------------------------------------------------------------------------------------------------
    def _inf_dist(self, ctx):
        return _trie_dist(self.root, self.start, ctx, self.params["backoff"])

    def phrase(self, ctx, prefix="", top=None, pm=None, use_train=True, min_p=0.5, max_extra=3):
        """One multi-word suggestion: (1) how a sentence that began exactly like this one went on, from the user's own
        sentences (weight 10) or the training text; else (2) the top word extended while the model is confident (>= min_p)."""
        best, bs = None, 0.0
        for idx, wgt in ((pm.idx if pm is not None else None, 10.0), (self.idx if use_train else None, 1.0)):
            for rem, c in (idx.get(tuple(ctx), {}).items() if idx else ()):
                if rem[0].startswith(prefix) and c * wgt > bs:
                    best, bs = rem, c * wgt
        if best:
            return list(best)
        if top and min_p < 1:
            ph, cap = [top], self.params["ctx_cap"]
            for _ in range(max_extra):
                d = self._inf_dist((list(ctx) + ph)[-cap:])
                if not d:
                    break
                w, p = max(d.items(), key=lambda x: x[1])
                if p < min_p:
                    break
                ph.append(w)
            if len(ph) > 1:
                return ph
        return None

    def score(self, ctx, cands):
        """Probability-like score of each candidate word given the context words (sums to 1 over cands)."""
        cap = self.params["ctx_cap"]
        c = ctx[-cap:] if cap else ctx
        d = self._inf_dist(c)
        raw = [d.get(w, 0.0) + 1e-6 * self.uni.get(w, 0) / self.T + 1e-12 for w in cands]
        z = sum(raw)
        inf = [x / z for x in raw]
        hist = " ".join(ctx) + (" " if ctx else "")
        chs = _softnorm([self.cm.logp_str(hist, w + " ") for w in cands])
        w_inf = self.params["w_inf"]
        return [w_inf * a + (1 - w_inf) * b for a, b in zip(inf, chs)]

    def rank(self, ctx, prefix=""):
        cands = self.candidates(prefix)
        if not cands:
            return []
        sc = self.score(list(ctx), cands)
        return sorted(zip(sc, cands), key=lambda x: -x[0])


# ───────────────────────────────────────────────── loading / serving ─────────────────────────────────────────────────────
_models = {}
_lock = threading.Lock()


def load_sentences(lang):
    """Training sentences for a language: predictor_data/<lang>.txt (one normalised sentence per line)."""
    p = os.path.join(DATA_DIR, f"{lang}.txt")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def get_model(lang):
    m = _models.get(lang)
    if m is None:
        with _lock:
            m = _models.get(lang)
            if m is None:
                sents = load_sentences(lang)
                if not sents:
                    return None
                m = LangModel(lang, sents)
                _models[lang] = m
    return m


def available(lang):
    return os.path.exists(os.path.join(DATA_DIR, f"{lang}.txt"))


def suggest_phrase(words, language, prefix="", top=None, personal=None):
    """The multi-word suggestion shown above the word list (a string), or None."""
    m = get_model(language) if language in LANGS else None
    if m is None:
        return None
    ctx = [w for t in words for w in words_of(t, language)]
    pre = "".join(words_of(prefix or "", language)) if prefix else ""
    ph = m.phrase(ctx, pre, top=top, pm=personal, **PHRASE)
    return " ".join(ph) if ph else None


PHRASE = {"use_train": True, "min_p": 0.5}     # chosen on dev (Step 16)


def predict(words, language, prefix="", top_k=10, emojis=None, use_lm=True, personal=None):
    """Ranked predictions for the next word (prefix == "") or the completion of a typed prefix.
    personal: a Personal model of this user's own sentences (optional).
    Returns [] when the language has no training data (caller falls back to the legacy predictor)."""
    if language not in LANGS:
        return []
    m = get_model(language)
    if m is None:
        return []
    ctx = [w for t in words for w in words_of(t, language)]
    pre = "".join(words_of(prefix or "", language)) if prefix else ""
    full = m.rank(ctx, pre)
    src = "model"
    if use_lm and full:                                    # optional GPU re-ranking of the shortlist (lm_rerank.py)
        try:
            import lm_rerank
            lm = lm_rerank.rerank(language, ctx, full)
            if lm is not None:
                full, src = lm, "model+lm"
        except Exception:
            pass                                           # any LM problem: keep the CPU ranking
    if personal is not None:
        full = personalise(full, personal, ctx, pre, LAM[language])
        src += "+personal" if personal.uni else ""
    ranked = full[:top_k]
    tot = sum(s for s, _ in ranked) or 1.0
    emojis = emojis or {}
    return [{"word": w, "prob": round(s / tot, 3), "emoji": emojis.get(w, "✨" if language != "en" else "💬"),
             "order": 0, "order_label": "v2", "source": src} for s, w in ranked]


def stats():
    return {"languages_loaded": {l: {"sentences": m.n_sentences, "vocab": len(m.uni)} for l, m in _models.items()},
            "languages_available": [l for l in LANGS if available(l)], "params": PARAMS, "cov_m": COV_M}
