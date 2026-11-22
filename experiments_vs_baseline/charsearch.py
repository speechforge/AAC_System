"""Re-implementation of the baseline paper's Section-3 search: next-CHARACTER distribution from a subword-token LLM
(remove the in-progress word's tokens from the context, beam-search token paths that regenerate it, marginalise the next char)."""
import torch, math, collections, string
SYMS = list(string.ascii_lowercase) + ["'", " "]
SIDX = {c: i for i, c in enumerate(SYMS)}

class CharSearchLM:
    def __init__(self, model, tok, beam=8, device="cuda"):
        self.m, self.tok, self.beam, self.dev = model.eval(), tok, beam, device
        V = model.get_input_embeddings().weight.shape[0]
        self.by_str = collections.defaultdict(list); self.pref = collections.defaultdict(list)
        first = torch.full((V,), -1, dtype=torch.long)
        for i in range(len(tok)):
            s = tok.convert_ids_to_tokens(i)
            if s is None or s in tok.all_special_tokens: continue
            s = s.replace("Ġ", " ").lower()
            if not s or any(c not in SIDX for c in s): continue
            self.by_str[s].append(i); first[i] = SIDX[s[0]]
            for k in range(1, len(s) + 1): self.pref[s[:k]].append(i)
        self.first = first.to(device); self.valid = (first >= 0).to(device)
        self.pref_t = {}; self.cache = {}; self.n_forward = 0
    def _ids(self, lst):
        return torch.tensor(lst, device=self.dev, dtype=torch.long)
    @torch.no_grad()
    def _logprobs(self, seqs):
        L = max(len(s) for s in seqs)
        ids = torch.full((len(seqs), L), self.tok.pad_token_id, dtype=torch.long); att = torch.zeros((len(seqs), L), dtype=torch.long)
        for i, s in enumerate(seqs): ids[i, :len(s)] = torch.tensor(s); att[i, :len(s)] = 1
        out = self.m(input_ids=ids.to(self.dev), attention_mask=att.to(self.dev)).logits
        self.n_forward += 1
        last = torch.tensor([len(s) - 1 for s in seqs], device=self.dev)
        return torch.log_softmax(out[torch.arange(len(seqs)), last].float(), -1)
    def next_char(self, text):
        if text in self.cache: return self.cache[text]
        if " " in text:
            fixed, part = text.rsplit(" ", 1); rem = " " + part
        else:
            fixed, rem = "", text
        bos = [self.tok.bos_token_id]
        base = bos + (self.tok(fixed, add_special_tokens=False)["input_ids"] if fixed else [])
        hyps = [(base, rem, 0.0)]; mass = torch.zeros(len(SYMS), device=self.dev)
        for _ in range(12):
            if not hyps: break
            lp = self._logprobs([h[0] for h in hyps]); new = []
            for hi, (seq, r, h_lp) in enumerate(hyps):
                p = lp[hi].exp(); w = math.exp(h_lp)
                if r == "":
                    bins = torch.zeros(len(SYMS), device=self.dev).index_add_(0, self.first[self.valid], p[self.valid]); mass += bins * w
                    continue
                for j in range(1, len(r) + 1):                      # tokens that are a prefix of the remaining string
                    for t in self.by_str.get(r[:j], ()):
                        new.append((seq + [t], r[j:], h_lp + float(lp[hi, t])))
                lst = self.pref.get(r)                              # tokens that extend past it: contribute the next char
                if lst:
                    key = r
                    if key not in self.pref_t:
                        ts = [t for t in lst if len(self._str(t)) > len(r)]
                        self.pref_t[key] = (self._ids(ts), self._ids([SIDX[self._str(t)[len(r)]] for t in ts])) if ts else None
                    pt = self.pref_t[key]
                    if pt is not None:
                        mass.index_add_(0, pt[1], p[pt[0]] * w)
            new.sort(key=lambda x: -x[2]); hyps = new[: self.beam]
        z = mass.sum().item()
        d = (mass / z).tolist() if z > 0 else [1 / len(SYMS)] * len(SYMS)
        self.cache[text] = d
        return d
    def _str(self, t):
        return self.tok.convert_ids_to_tokens(t).replace("Ġ", " ").lower()
    def logp_sentence(self, s):
        return sum(math.log(max(self.next_char(s[:i])[SIDX[c]], 1e-12)) for i, c in enumerate(s))
