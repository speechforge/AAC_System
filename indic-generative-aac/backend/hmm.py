import pickle
import os
from collections import defaultdict, Counter

class AACHMM:
    def __init__(self):
        self.bigrams = defaultdict(Counter)
        self.trigrams = defaultdict(Counter)
        self.sentence_count = 0
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

        # 2. Load General/English HMM
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hmm_model.pkl')
        model_path = local_path if os.path.exists(local_path) else '/home/linux/Documents/2026/aac_system_demo_track/indic-generative-aac/backend/hmm_model.pkl'
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
                self.bigrams = data['bigrams']
                self.trigrams = data['trigrams']
                self.sentence_count = data.get('sentence_count', len(self.bigrams))
            print(f"[HMM Engine] Loaded general model: {len(self.bigrams)} bigram states.")

    def reload(self):
        self.train()

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

        # Fallback to English HMM
        if not current_words:
            return [{"word": w, "prob": 0.2, "emoji": "💬"} for w in ["i", "can", "where", "please", "yes"]]

        words = [w.lower() for w in current_words]
        candidates = Counter()

        if len(words) >= 2:
            context = (words[-2], words[-1])
            if context in self.trigrams:
                candidates.update(self.trigrams[context])

        if not candidates and len(words) >= 1:
            context = words[-1]
            if context in self.bigrams:
                candidates.update(self.bigrams[context])

        if not candidates:
            return []

        total = sum(candidates.values()) or 1
        return [{"word": w, "prob": round(c / total, 3), "emoji": "💬"} for w, c in candidates.most_common(top_k)]

hmm_engine = AACHMM()

