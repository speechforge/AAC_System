import pickle
import os
import sys
from collections import defaultdict, Counter

# Ensure infinity_gram engine is loaded for arbitrary-depth n-gram modeling
try:
    from infinity_gram import infinity_gram_engine
except ImportError:
    infinity_gram_engine = None

# Ensure dual_hmm_streaming_kit is accessible for class definitions
DUAL_KIT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../dual_hmm_streaming_kit"))
if DUAL_KIT_DIR not in sys.path:
    sys.path.insert(0, DUAL_KIT_DIR)

try:
    from models_def import AACNextWordHMM, AACUnjumbleHMM, COMMON_EMOJIS
except ImportError:
    COMMON_EMOJIS = {
        "water": "💧", "food": "🍲", "eat": "🍽️", "drink": "🥤", "want": "🙋", "help": "🆘",
        "please": "🙏", "thanks": "✨", "thank": "✨", "yes": "✅", "no": "❌", "i": "👤",
        "you": "👉", "pain": "🤕", "doctor": "👨‍⚕️", "medicine": "💊", "bathroom": "🚻",
        "sleep": "😴", "tired": "🥱", "happy": "😊", "sad": "😢", "angry": "😠", "cold": "❄️",
        "hot": "🔥", "home": "🏠", "go": "🚶", "come": "🏃", "see": "👀", "listen": "👂"
    }

class AACHMM:
    def __init__(self):
        self.infinity_gram = infinity_gram_engine
        self.unigrams = Counter()
        self.bigrams = defaultdict(Counter)
        self.trigrams = defaultdict(Counter)
        self.fourgrams = defaultdict(Counter)
        self.start_priors = Counter()
        self.sentence_count = 0
        self.unjumble_model = None

        self.hindi_priors = Counter()
        self.hindi_bigrams = defaultdict(Counter)
        self.hindi_trigrams = defaultdict(Counter)
        self.hindi_emojis = {}
        self.hindi_vocab = []
        self.train()

    def train(self):
        # 1. Load Hindi AAC HMM
        hindi_model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hmm_hindi.pkl')
        if os.path.exists(hindi_model_path):
            try:
                with open(hindi_model_path, 'rb') as f:
                    h_data = pickle.load(f)
                    self.hindi_priors = Counter(h_data.get('priors', {}))
                    self.hindi_bigrams = defaultdict(Counter, {k: Counter(v) for k, v in h_data.get('bigrams', {}).items()})
                    self.hindi_trigrams = defaultdict(Counter, {k: Counter(v) for k, v in h_data.get('trigrams', {}).items()})
                    self.hindi_emojis = h_data.get('emojis', {})
                    self.hindi_vocab = h_data.get('vocab', [])
                print(f"[HMM Engine] Loaded Hindi AAC model: {len(self.hindi_vocab)} vocab, {len(self.hindi_bigrams)} bigrams, {len(self.hindi_trigrams)} trigrams.")
            except Exception as e:
                print(f"[HMM Engine] Error loading hmm_hindi.pkl: {e}")

        # 2. Load General/English HMM — try Dual HMM kit first, fall back to built-in vocab
        dual_hmm1_path = os.path.join(DUAL_KIT_DIR, "models", "hmm1_nextword_latest.pkl")
        if os.path.exists(dual_hmm1_path):
            try:
                with open(dual_hmm1_path, 'rb') as f:
                    h1_data = pickle.load(f)
                # hmm1 stores fourgrams as {(w1,w2,w3): Counter(next_word→count)}
                # We map this into our bigrams/trigrams/fourgrams structure
                raw_fg = h1_data.get('fourgrams', {})
                for ctx_tuple, next_counts in raw_fg.items():
                    if len(ctx_tuple) == 3:
                        self.fourgrams[ctx_tuple] = next_counts
                        # Also populate trigram from last 2 of context
                        tri_key = (ctx_tuple[1], ctx_tuple[2])
                        for w, c in next_counts.items():
                            self.trigrams[tri_key][w] += c
                        # And bigram from last 1
                        bi_key = ctx_tuple[2]
                        for w, c in next_counts.items():
                            self.bigrams[bi_key][w] += c
                    elif len(ctx_tuple) == 2:
                        self.trigrams[ctx_tuple] = next_counts
                        bi_key = ctx_tuple[1]
                        for w, c in next_counts.items():
                            self.bigrams[bi_key][w] += c
                    elif len(ctx_tuple) == 1:
                        self.bigrams[ctx_tuple[0]] = next_counts
                self.sentence_count = h1_data.get('sentence_count', len(raw_fg))
                # Build unigram from bigram values
                for bi_key, next_ctr in self.bigrams.items():
                    self.unigrams[bi_key] += sum(next_ctr.values())
                # Build start_priors: words that follow sentence-start markers
                for ctx, nxt in self.fourgrams.items():
                    if ctx[2] in ('i', 'please', 'can', 'help', 'do', 'my'):
                        self.start_priors[ctx[2]] += sum(nxt.values())
                if not self.start_priors:
                    for w in ['i', 'please', 'can', 'help', 'yes', 'no']:
                        if w in self.unigrams:
                            self.start_priors[w] = self.unigrams[w]
                print(f"[HMM Engine] Loaded Dual HMM-1: {self.sentence_count:,} sentences, "
                      f"{len(self.fourgrams):,} 4-gram contexts, {len(self.trigrams):,} trigrams, "
                      f"{len(self.bigrams):,} bigrams.")
            except Exception as e:
                print(f"[HMM Engine] Failed to load Dual HMM-1: {e}. Falling back to built-in vocab.")
                self._load_builtin_english_vocab()
        else:
            print(f"[HMM Engine] Dual HMM-1 not found at {dual_hmm1_path}. Using built-in vocab.")
            self._load_builtin_english_vocab()

        # Try loading HMM-2 (unjumble) — optional, large file
        dual_hmm2_path = os.path.join(DUAL_KIT_DIR, "models", "hmm2_unjumble_latest.pkl")
        if os.path.exists(dual_hmm2_path):
            try:
                with open(dual_hmm2_path, 'rb') as f:
                    h2_data = pickle.load(f)
                # Store raw for unjumble
                self._unjumble_data = h2_data
                self.unjumble_model = h2_data
                print(f"[HMM Engine] Loaded Dual HMM-2 (unjumble): {type(h2_data)}")
            except Exception as e:
                print(f"[HMM Engine] Failed to load HMM-2: {e}. Unjumble will return input order.")

    def _load_builtin_english_vocab(self):
        """Minimal built-in AAC English HMM — no file loading, zero RAM cost."""
        aac_phrases = [
            ["i", "want", "water"], ["i", "need", "help"], ["i", "feel", "pain"],
            ["please", "help", "me"], ["i", "want", "food"], ["i", "need", "medicine"],
            ["i", "want", "go", "home"], ["can", "you", "help"], ["i", "am", "tired"],
            ["i", "am", "hungry"], ["i", "am", "thirsty"], ["i", "am", "cold"],
            ["i", "am", "hot"], ["i", "need", "bathroom"], ["call", "doctor", "please"],
            ["i", "want", "sleep"], ["i", "feel", "happy"], ["i", "feel", "sad"],
            ["yes", "please"], ["no", "thank", "you"], ["i", "love", "you"],
            ["good", "morning"], ["good", "night"], ["i", "want", "more"],
            ["stop", "please"], ["i", "do", "not", "want"], ["i", "am", "okay"],
            ["can", "i", "have"], ["i", "want", "to", "go"], ["please", "wait"],
            ["i", "need", "rest"], ["it", "hurts", "here"], ["call", "my", "family"],
            ["i", "want", "music"], ["turn", "off", "light"], ["turn", "on", "light"],
            ["i", "am", "angry"], ["i", "do", "not", "understand"], ["please", "repeat"],
            ["i", "want", "sit"], ["i", "want", "stand"], ["i", "need", "wheelchair"],
        ]
        for sent in aac_phrases:
            for i, w in enumerate(sent):
                self.unigrams[w] += 1
                if i == 0:
                    self.start_priors[w] += 1
                if i >= 1:
                    self.bigrams[sent[i-1]][w] += 1
                if i >= 2:
                    self.trigrams[(sent[i-2], sent[i-1])][w] += 1
        self.sentence_count = len(aac_phrases)
        print(f"[HMM Engine] Built-in AAC vocab: {len(self.unigrams)} words, {len(self.bigrams)} bigrams, {self.sentence_count} seed phrases.")

    def reload(self):
        self.train()

    def unjumble(self, words):
        """Reconstruct canonical syntactic sequence from disordered words using HMM-2."""
        if not words:
            return [], 0.0
        if self.unjumble_model is not None:
            return self.unjumble_model.unjumble(words)
        return words, 0.0

    def predict_next(self, current_words, language="hi", top_k=5):
        # ── 1. Primary Engine: Infinity-Gram (∞-gram) with Arbitrary Context Depth ──
        if self.infinity_gram is not None:
            try:
                inf_preds = self.infinity_gram.predict_next(current_words, language=language, top_k=top_k)
                if inf_preds:
                    return inf_preds
            except Exception as e:
                print(f"[HMM Engine] Infinity-Gram fallback to Markov: {e}")

        # ── 2. Fallback Engine: Legacy Fixed 3-gram / 4-gram Markov Model ──
        # Determine if input is Hindi
        is_hindi = (language == "hi") or any(any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in w) for w in current_words)
        
        if is_hindi and self.hindi_bigrams:
            clean_words = [w.strip() for w in current_words if w.strip()]
            
            # Initial state (no words selected yet) -> recommend most useful starting AAC entities
            if not clean_words:
                top_priors = self.hindi_priors.most_common(top_k) or [("माँ", 10), ("डॉक्टर", 8), ("पापा", 8), ("दोस्त", 6), ("पानी", 6)]
                total = sum(c for _, c in top_priors) or 1
                return [{
                    "word": w,
                    "prob": round(c / total, 3),
                    "emoji": self.hindi_emojis.get(w, "✨")
                } for w, c in top_priors]

            candidates = Counter()
            selected_set = set(clean_words)

            # High-order Trigram Markov transition
            if len(clean_words) >= 2:
                tri_key = (clean_words[-2], clean_words[-1])
                if tri_key in self.hindi_trigrams:
                    for cand, count in self.hindi_trigrams[tri_key].items():
                        if cand not in selected_set:
                            candidates[cand] += count * 4

            # Bigram Markov transition
            bi_key = clean_words[-1]
            if bi_key in self.hindi_bigrams:
                for cand, count in self.hindi_bigrams[bi_key].items():
                    if cand not in selected_set:
                        candidates[cand] += count * 2

            # Smooth backoff if fewer candidates
            if len(candidates) < top_k:
                for w, c in self.hindi_priors.most_common(12):
                    if w not in selected_set and w not in candidates:
                        candidates[w] += 1

            total = sum(candidates.values()) or 1
            return [{
                "word": w,
                "prob": round(c / total, 3),
                "emoji": self.hindi_emojis.get(w, "✨")
            } for w, c in candidates.most_common(top_k)]

        # Scaled English HMM
        clean_words = [w.lower().strip() for w in current_words if w.strip()]
        selected_set = set(clean_words)

        # Empty context -> start-of-sentence priors
        if not clean_words:
            if self.start_priors:
                top_starts = self.start_priors.most_common(top_k)
                tot = sum(c for _, c in top_starts) or 1
                return [{
                    "word": w,
                    "prob": round(c / tot, 3),
                    "emoji": COMMON_EMOJIS.get(w, "💬")
                } for w, c in top_starts]
            return [{"word": w, "prob": 0.2, "emoji": COMMON_EMOJIS.get(w, "💬")} for w in ["i", "please", "can", "help", "yes"]]

        candidates = Counter()

        # 4-gram context
        if len(clean_words) >= 3 and self.fourgrams:
            ctx4 = (clean_words[-3], clean_words[-2], clean_words[-1])
            if ctx4 in self.fourgrams:
                for cand, cnt in self.fourgrams[ctx4].items():
                    if cand not in selected_set:
                        candidates[cand] += cnt * 6

        # Trigram context
        if len(clean_words) >= 2 and self.trigrams:
            ctx3 = (clean_words[-2], clean_words[-1])
            if ctx3 in self.trigrams:
                for cand, cnt in self.trigrams[ctx3].items():
                    if cand not in selected_set:
                        candidates[cand] += cnt * 3

        # Bigram context
        if len(clean_words) >= 1 and self.bigrams:
            ctx2 = clean_words[-1]
            if ctx2 in self.bigrams:
                for cand, cnt in self.bigrams[ctx2].items():
                    if cand not in selected_set:
                        candidates[cand] += cnt * 1

        # Unigram backoff
        if len(candidates) < top_k and self.unigrams:
            for w, cnt in self.unigrams.most_common(top_k * 2):
                if w not in selected_set and w not in candidates:
                    candidates[w] += 1

        if not candidates:
            return []

        total = sum(candidates.values()) or 1
        return [{
            "word": w,
            "prob": round(c / total, 3),
            "emoji": COMMON_EMOJIS.get(w, "💬")
        } for w, c in candidates.most_common(top_k)]

hmm_engine = AACHMM()

