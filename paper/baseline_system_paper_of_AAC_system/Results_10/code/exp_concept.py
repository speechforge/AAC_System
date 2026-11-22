"""Experiment 6: concept-level next-symbol predictor (the shipped predictor for gu/mr, and a complement for en/hi)."""
import sys, json, collections
from lib import *
import aac_lexicon as L, concept_predict as CP
res = {}
for lang in sys.argv[1:]:
    test = sents(lang, "test"); hits = collections.Counter(); n = 0; words = covered = 0; seqs = 0
    for s in test:
        cids = []
        for w in s.split():
            words += 1; c = L.resolve_label(w, lang)
            if c: cids.append(c); covered += 1
        if len(cids) < 2: continue
        seqs += 1
        for i in range(1, len(cids)):
            if cids[i] in cids[:i]: continue            # predictor never re-offers a selected symbol
            preds = [p["cid"] for p in CP.predict(s.split() and [L.BOARD[c][lang] for c in cids[:i]], lang, 10)]
            n += 1
            for K in (1, 3, 5, 10):
                if cids[i] in preds[:K]: hits[K] += 1
    res[lang] = dict(n_test_sentences=len(test), sentences_with_2plus_concepts=seqs, next_concept_events=n, word_to_concept_coverage_pct=100 * covered / max(words, 1),
                     hit_pct={K: 100 * hits[K] / max(n, 1) for K in (1, 3, 5, 10)})
    print(lang, res[lang], flush=True)
json.dump(res, open("results/concept_" + "_".join(sys.argv[1:]) + ".json", "w"), indent=1)
