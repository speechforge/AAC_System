import pickle
import os
import sys
from collections import defaultdict, Counter

# Ensure dual_hmm_streaming_kit is accessible for class definitions
DUAL_KIT_DIR = "/home/linux/Documents/AACsystem/AAC_System-jaydeep/dual_hmm_streaming_kit"
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

        # 2. Load General/English HMM (lightweight stub mode — skips all large pkl files)
        # Both hmm2_unjumble_latest.pkl (~709MB) and hmm_model.pkl (~768MB) are too large
        # to load alongside the training process. Use built-in minimal AAC vocab instead.
        print("[HMM Engine] Using lightweight built-in English AAC vocab (training is running in parallel).")
        self._load_builtin_english_vocab()
        return

        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hmm_model.pkl')
        model_path = local_path if os.path.exists(local_path) else '/home/linux/Documents/2026/aac_system_demo_track/indic-generative-aac/backend/hmm_model.pkl'
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.bigrams = data.get('bigrams', defaultdict(Counter))
                    self.trigrams = data.get('trigrams', defaultdict(Counter))
                    self.fourgrams = data.get('fourgrams', defaultdict(Counter))
                    self.start_priors = data.get('start_priors', Counter())
                    self.unigrams = data.get('unigrams', Counter())
                    self.sentence_count = data.get('sentence_count', len(self.bigrams))
                    self.unjumble_model = data.get('unjumble_model', None)
                print(f"[HMM Engine] Loaded enhanced dual model: {self.sentence_count:,} sentences, {len(self.bigrams):,} bigrams, {len(self.trigrams):,} trigrams, unjumble_available={self.unjumble_model is not None}.")
            except Exception as e:
                print(f"[HMM Engine] Error loading hmm_model.pkl: {e}")

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

