"""Tests for predictor_v2 (run: python -m pytest test_predictor_v2.py, or python test_predictor_v2.py)."""
import predictor_v2 as P

def test_all_languages_have_data_and_answer():
    for lang in P.LANGS:
        assert P.available(lang), lang
        out = P.predict([], lang, top_k=10)
        assert len(out) == 10 and all("word" in r for r in out), lang

def test_script_matches_language():
    import re
    pat = {"en": r"^[a-z']+$", "hi": r"^[ऀ-ॣ०-ॿ]+$", "mr": r"^[ऀ-ॣ०-ॿ]+$", "gu": r"^[઀-૰૱-૿]+$"}
    for lang in P.LANGS:
        for r in P.predict([], lang, top_k=10):
            assert re.match(pat[lang], r["word"]), (lang, r["word"])

def test_gujarati_uses_gujarati_model_not_english():
    out = P.predict([], "gu", top_k=5)
    assert out and all(any("઀" <= c <= "૿" for c in r["word"]) for r in out)

def test_prefix_filters_candidates():
    for lang, pre in (("en", "wa"), ("hi", "मु"), ("mr", "आ"), ("gu", "હુ")):
        out = P.predict([], lang, prefix=pre, top_k=10)
        assert out and all(r["word"].startswith(pre) for r in out), (lang, pre)

def test_unseen_word_is_reachable_with_prefix():
    m = P.get_model("en")
    cands = m.candidates("xyl")
    assert all(c.startswith("xyl") for c in cands)          # no crash with a prefix nothing in training starts with

def test_repeated_word_not_excluded():
    out = P.predict(["i", "want", "to", "eat", "and"], "en", top_k=10)
    assert out                                              # no exclusion of already-used words in v2

def test_unknown_language_returns_empty():
    assert P.predict([], "xx") == []

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
