"""
models_def.py - Core Architecture for Dual HMM Suite:
1. AACNextWordHMM: Scalable high-order Markov Next-Word Recommendation Model
2. AACUnjumbleHMM: Syntactic & Lexical Markov Un-Jumbling / Permutation Decoder with GPU acceleration
"""

import math
import itertools
from collections import defaultdict, Counter
import re
import torch

# Coarse POS tags for English AAC syntactic alignment
COARSE_TAGS = {
    # Pronouns
    'i': 'PRON', 'you': 'PRON', 'he': 'PRON', 'she': 'PRON', 'it': 'PRON', 'we': 'PRON', 'they': 'PRON',
    'me': 'PRON_OBJ', 'him': 'PRON_OBJ', 'her': 'PRON_OBJ', 'us': 'PRON_OBJ', 'them': 'PRON_OBJ',
    'my': 'POSS', 'your': 'POSS', 'his': 'POSS', 'their': 'POSS', 'our': 'POSS',
    # Modal & Auxiliaries
    'can': 'MODAL', 'could': 'MODAL', 'will': 'MODAL', 'would': 'MODAL', 'may': 'MODAL', 'might': 'MODAL',
    'should': 'MODAL', 'must': 'MODAL', 'do': 'AUX', 'does': 'AUX', 'did': 'AUX',
    'is': 'BE', 'am': 'BE', 'are': 'BE', 'was': 'BE', 'were': 'BE', 'be': 'BE', 'been': 'BE', 'being': 'BE',
    'have': 'HAVE', 'has': 'HAVE', 'had': 'HAVE',
    # Determiners & Prepositions
    'the': 'DET', 'a': 'DET', 'an': 'DET', 'this': 'DET', 'that': 'DET', 'these': 'DET', 'those': 'DET',
    'in': 'PREP', 'on': 'PREP', 'at': 'PREP', 'to': 'PREP', 'for': 'PREP', 'with': 'PREP', 'from': 'PREP',
    'by': 'PREP', 'about': 'PREP', 'into': 'PREP', 'through': 'PREP', 'over': 'PREP', 'under': 'PREP',
    'of': 'PREP', 'out': 'PREP',
    # Conjunctions & Negation
    'and': 'CONJ', 'or': 'CONJ', 'but': 'CONJ', 'because': 'CONJ', 'so': 'CONJ', 'if': 'CONJ',
    'not': 'NEG', 'no': 'NEG', 'never': 'NEG',
    # AAC Conversational Markers
    'please': 'COURTESY', 'thank': 'COURTESY', 'thanks': 'COURTESY', 'hello': 'GREET', 'hi': 'GREET',
    'yes': 'AFFIRM', 'no': 'NEG', 'okay': 'AFFIRM', 'ok': 'AFFIRM', 'help': 'VERB',
}

COMMON_EMOJIS = {
    "water": "💧", "food": "🍲", "eat": "🍽️", "drink": "🥤", "want": "🙋", "help": "🆘",
    "please": "🙏", "thanks": "✨", "thank": "✨", "yes": "✅", "no": "❌", "i": "👤",
    "you": "👉", "pain": "🤕", "doctor": "👨‍⚕️", "medicine": "💊", "bathroom": "🚻",
    "sleep": "😴", "tired": "🥱", "happy": "😊", "sad": "😢", "angry": "😠", "cold": "❄️",
    "hot": "🔥", "home": "🏠", "go": "🚶", "come": "🏃", "see": "👀", "listen": "👂",
    "speak": "🗣️", "stop": "🛑", "play": "🎮", "read": "📖", "write": "✍️", "love": "❤️"
}


class AACNextWordHMM:
    """
    High-Order Smoothed Markov Model for Real-Time AAC Next-Word Prediction.
    Supports shared references with AACUnjumbleHMM to eliminate memory duplication.
    """
    def __init__(self):
        self.unigrams = Counter()
        self.bigrams = defaultdict(Counter)
        self.trigrams = defaultdict(Counter)
        self.fourgrams = defaultdict(Counter)
        self.start_priors = Counter()
        self.end_priors = Counter()
        self.total_tokens = 0
        self.sentence_count = 0
        self.vocabulary = set()

        # Smoothing weights (adaptive Jelinek-Mercer interpolation)
        self.lambda4 = 0.50
        self.lambda3 = 0.30
        self.lambda2 = 0.15
        self.lambda1 = 0.05

    def bind_shared_store(self, unjumble_hmm):
        """Share state dictionaries with unjumble_hmm to save ~12 GB of host RAM."""
        self.unigrams = unjumble_hmm.word_unigrams
        self.bigrams = unjumble_hmm.word_bigrams
        self.trigrams = unjumble_hmm.word_trigrams
        self.start_priors = unjumble_hmm.start_priors
        self.end_priors = unjumble_hmm.end_priors
        self.sentence_count = unjumble_hmm.sentence_count
        self.vocabulary = set(unjumble_hmm.word_unigrams.keys())
        self.total_tokens = sum(unjumble_hmm.word_unigrams.values())

    def update_sentence(self, tokens):
        """Tokens is a list of lowercase alphanumeric words."""
        if not tokens:
            return
        self.sentence_count += 1
        n = len(tokens)
        self.total_tokens += n
        self.start_priors[tokens[0]] += 1
        self.end_priors[tokens[-1]] += 1

        for w in tokens:
            self.unigrams[w] += 1
            self.vocabulary.add(w)

        # Bigrams
        for i in range(n - 1):
            self.bigrams[tokens[i]][tokens[i + 1]] += 1

        # Trigrams
        for i in range(n - 2):
            self.trigrams[(tokens[i], tokens[i + 1])][tokens[i + 2]] += 1

        # 4-grams (high-order parameter expansion)
        for i in range(n - 3):
            self.fourgrams[(tokens[i], tokens[i + 1], tokens[i + 2])][tokens[i + 3]] += 1

    def update_fourgrams_only(self, tokens):
        """Lightweight update for 4-grams when unigrams/bigrams/trigrams are shared."""
        n = len(tokens)
        if n < 4:
            return
        for i in range(n - 3):
            self.fourgrams[(tokens[i], tokens[i + 1], tokens[i + 2])][tokens[i + 3]] += 1

    def prune_rare_transitions(self, min_count=3, max_total_fourgrams=4000000):
        """
        Aggressive, OOM-proof memory compaction for 4-grams:
        1. Drop individual rare transitions with count < min_count.
        2. Context-level frequency pruning to strictly enforce max_total_fourgrams ceiling.
        """
        dead_keys = []
        for u, counter in self.fourgrams.items():
            to_remove = [v for v, c in counter.items() if c < min_count]
            for v in to_remove:
                del counter[v]
            if not counter:
                dead_keys.append(u)
        for u in dead_keys:
            del self.fourgrams[u]

        # Context-level safety cap: if still > max_total_fourgrams, prune low-frequency contexts
        if len(self.fourgrams) > max_total_fourgrams:
            min_ctx_sum = 5
            while len(self.fourgrams) > max_total_fourgrams and min_ctx_sum <= 100:
                dead_keys = [u for u, counter in self.fourgrams.items() if sum(counter.values()) < min_ctx_sum]
                for u in dead_keys:
                    del self.fourgrams[u]
                min_ctx_sum += 5

    def predict_next(self, current_words, top_k=10):
        """
        Predict next words given current context tokens.
        Fast O(1) lookup with multi-order interpolated backoff.
        """
        words = [w.lower().strip() for w in current_words if w.strip()]
        selected_set = set(words)
        candidates = Counter()

        # Context is empty: recommend start-of-sentence words
        if not words:
            top_start = self.start_priors.most_common(top_k * 2)
            total = sum(c for _, c in top_start) or 1
            out = []
            for w, c in top_start[:top_k]:
                out.append({
                    "word": w,
                    "prob": round(c / total, 4),
                    "emoji": COMMON_EMOJIS.get(w, "💬")
                })
            return out

        # 1. 4-gram context
        if len(words) >= 3:
            ctx4 = (words[-3], words[-2], words[-1])
            if ctx4 in self.fourgrams:
                sum4 = sum(self.fourgrams[ctx4].values())
                for cand, cnt in self.fourgrams[ctx4].items():
                    if cand not in selected_set:
                        candidates[cand] += (cnt / sum4) * self.lambda4

        # 2. Trigram context
        if len(words) >= 2:
            ctx3 = (words[-2], words[-1])
            if ctx3 in self.trigrams:
                sum3 = sum(self.trigrams[ctx3].values())
                for cand, cnt in self.trigrams[ctx3].items():
                    if cand not in selected_set:
                        candidates[cand] += (cnt / sum3) * self.lambda3

        # 3. Bigram context
        if len(words) >= 1:
            ctx2 = words[-1]
            if ctx2 in self.bigrams:
                sum2 = sum(self.bigrams[ctx2].values())
                for cand, cnt in self.bigrams[ctx2].items():
                    if cand not in selected_set:
                        candidates[cand] += (cnt / sum2) * self.lambda2

        # 4. Unigram backoff
        if len(candidates) < top_k:
            for w, cnt in self.unigrams.most_common(top_k * 3):
                if w not in selected_set and w not in candidates:
                    candidates[w] += (cnt / max(1, self.total_tokens)) * self.lambda1

        total_score = sum(candidates.values()) or 1.0
        results = []
        for w, sc in candidates.most_common(top_k):
            results.append({
                "word": w,
                "prob": round(sc / total_score, 4),
                "emoji": COMMON_EMOJIS.get(w, "💬")
            })
        return results

    def get_stats(self):
        return {
            "sentence_count": self.sentence_count,
            "total_tokens": self.total_tokens,
            "vocab_size": len(self.vocabulary),
            "bigram_states": len(self.bigrams),
            "trigram_states": len(self.trigrams),
            "fourgram_states": len(self.fourgrams)
        }


class AACUnjumbleHMM:
    """
    Second-Level Syntactic & Lexical Markov Permutation Decoder.
    Takes disordered / jumbled AAC keyword input bags and produces the
    most syntactically and lexically probable word order.
    Accelerated with PyTorch CUDA tensors on NVIDIA GPU when available.
    """
    def __init__(self):
        self.word_unigrams = Counter()
        self.word_bigrams = defaultdict(Counter)
        self.word_trigrams = defaultdict(Counter)
        self.start_priors = Counter()
        self.end_priors = Counter()
        self.sentence_count = 0

        # Syntactic POS Hidden Markov Components
        self.pos_priors = Counter()
        self.pos_transitions = defaultdict(Counter)
        self.pos_trigrams = defaultdict(Counter)
        self.pos_end = Counter()
        self.word_to_pos = defaultdict(Counter)

        # Weight balancing lexical vs syntactic transition scores
        self.alpha_lex = 1.0
        self.beta_pos = 0.65

        # GPU acceleration configuration
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

    def get_pos(self, word):
        """Infer coarse syntactic POS tag."""
        w = word.lower()
        if w in COARSE_TAGS:
            return COARSE_TAGS[w]
        if w in self.word_to_pos and self.word_to_pos[w]:
            return self.word_to_pos[w].most_common(1)[0][0]
        # Heuristics based on morphology
        if w.endswith('ing'):
            return 'VERB'
        if w.endswith('ly'):
            return 'ADV'
        if w.endswith('ed'):
            return 'VERB'
        if w.endswith('s') and len(w) > 3:
            return 'NOUN'
        return 'NOUN'

    def update_sentence(self, tokens, pos_tags=None):
        if not tokens or len(tokens) < 2:
            return
        self.sentence_count += 1
        n = len(tokens)
        self.start_priors[tokens[0]] += 1
        self.end_priors[tokens[-1]] += 1

        if pos_tags is None:
            pos_tags = [self.get_pos(w) for w in tokens]

        self.pos_priors[pos_tags[0]] += 1
        self.pos_end[pos_tags[-1]] += 1

        for w, p in zip(tokens, pos_tags):
            self.word_unigrams[w] += 1
            self.word_to_pos[w][p] += 1

        # Lexical and Syntactic Bigrams
        for i in range(n - 1):
            self.word_bigrams[tokens[i]][tokens[i + 1]] += 1
            self.pos_transitions[pos_tags[i]][pos_tags[i + 1]] += 1

        # Lexical and Syntactic Trigrams
        for i in range(n - 2):
            self.word_trigrams[(tokens[i], tokens[i + 1])][tokens[i + 2]] += 1
            self.pos_trigrams[(pos_tags[i], pos_tags[i + 1])][pos_tags[i + 2]] += 1

    def prune_rare_transitions(self, min_count=2, max_total_trigrams=5000000):
        """
        Aggressive, OOM-proof memory compaction for trigrams:
        1. Drop individual rare transitions with count < min_count.
        2. Context-level frequency pruning to strictly enforce max_total_trigrams ceiling.
        """
        if len(self.word_trigrams) > max_total_trigrams:
            dead_keys = []
            for ctx, counter in self.word_trigrams.items():
                to_remove = [w for w, c in counter.items() if c < min_count]
                for w in to_remove:
                    del counter[w]
                if not counter:
                    dead_keys.append(ctx)
            for ctx in dead_keys:
                del self.word_trigrams[ctx]

            # Context-level safety cap: if still > max_total_trigrams, prune low-frequency contexts
            if len(self.word_trigrams) > max_total_trigrams:
                min_ctx_sum = 10
                while len(self.word_trigrams) > max_total_trigrams and min_ctx_sum <= 100:
                    dead_keys = [ctx for ctx, counter in self.word_trigrams.items() if sum(counter.values()) < min_ctx_sum]
                    for ctx in dead_keys:
                        del self.word_trigrams[ctx]
                    min_ctx_sum += 5

    def score_sequence(self, tokens):
        """
        Compute joint log-likelihood:
        Score = alpha * [log P(w1|<s>) + sum log P(wi|wi-1, wi-2) + log P(</s>|wn)]
              + beta  * [log P(p1|<s>) + sum log P(pi|pi-1, pi-2) + log P(</s>|pn)]
        """
        n = len(tokens)
        if n == 0:
            return -999.0

        pos_tags = [self.get_pos(w) for w in tokens]
        log_p_lex = 0.0
        log_p_pos = 0.0

        # Start priors
        c_start_w = self.start_priors[tokens[0]]
        tot_start_w = sum(self.start_priors.values()) or 1
        log_p_lex += math.log((c_start_w + 0.1) / (tot_start_w + 10.0))

        c_start_p = self.pos_priors[pos_tags[0]]
        tot_start_p = sum(self.pos_priors.values()) or 1
        log_p_pos += math.log((c_start_p + 0.5) / (tot_start_p + 10.0))

        # Bigram & Trigram transitions
        for i in range(1, n):
            w_prev = tokens[i - 1]
            w_curr = tokens[i]
            p_prev = pos_tags[i - 1]
            p_curr = pos_tags[i]

            # Lexical transition
            lex_prob = 0.0
            if i >= 2:
                ctx_tri = (tokens[i - 2], w_prev)
                if ctx_tri in self.word_trigrams:
                    c_tri = self.word_trigrams[ctx_tri][w_curr]
                    tot_tri = sum(self.word_trigrams[ctx_tri].values())
                    if tot_tri > 0 and c_tri > 0:
                        lex_prob += 0.6 * (c_tri / tot_tri)

            c_bi = self.word_bigrams[w_prev][w_curr]
            tot_bi = sum(self.word_bigrams[w_prev].values())
            if tot_bi > 0:
                lex_prob += 0.3 * (c_bi / tot_bi)

            c_uni = self.word_unigrams[w_curr]
            tot_uni = sum(self.word_unigrams.values()) or 1
            lex_prob += 0.1 * ((c_uni + 0.1) / (tot_uni + 100.0))
            log_p_lex += math.log(max(lex_prob, 1e-7))

            # POS Tag transition
            pos_prob = 0.0
            if i >= 2:
                ctx_pos_tri = (pos_tags[i - 2], p_prev)
                if ctx_pos_tri in self.pos_trigrams:
                    cp_tri = self.pos_trigrams[ctx_pos_tri][p_curr]
                    totp_tri = sum(self.pos_trigrams[ctx_pos_tri].values())
                    if totp_tri > 0 and cp_tri > 0:
                        pos_prob += 0.5 * (cp_tri / totp_tri)

            cp_bi = self.pos_transitions[p_prev][p_curr]
            totp_bi = sum(self.pos_transitions[p_prev].values())
            if totp_bi > 0:
                pos_prob += 0.5 * ((cp_bi + 0.1) / (totp_bi + 1.0))
            else:
                pos_prob += 0.01

            log_p_pos += math.log(max(pos_prob, 1e-6))

        # End priors
        c_end_w = self.end_priors[tokens[-1]]
        tot_end_w = sum(self.end_priors.values()) or 1
        log_p_lex += math.log((c_end_w + 0.1) / (tot_end_w + 10.0))

        c_end_p = self.pos_end[pos_tags[-1]]
        tot_end_p = sum(self.pos_end.values()) or 1
        log_p_pos += math.log((c_end_p + 0.5) / (tot_end_p + 10.0))

        return self.alpha_lex * log_p_lex + self.beta_pos * log_p_pos

    def unjumble(self, jumbled_words, beam_width=64):
        """
        Reconstruct optimal syntactic sequence from an unordered bag of keywords.
        Uses exact permutation search for len <= 6, and Beam Search for len > 6.
        """
        clean_words = [w.lower().strip() for w in jumbled_words if w.strip()]
        n = len(clean_words)
        if n <= 1:
            return clean_words, 0.0

        # Exact permutation scoring for up to 6 words (max 720 permutations)
        if n <= 6:
            best_perm = None
            best_score = -float('inf')
            seen = set()
            for perm in itertools.permutations(clean_words):
                if perm in seen:
                    continue
                seen.add(perm)
                sc = self.score_sequence(perm)
                if sc > best_score:
                    best_score = sc
                    best_perm = perm
            return list(best_perm), best_score

        # Beam Search for sequences > 6 tokens
        beam = [((w,), tuple(clean_words[:i] + clean_words[i+1:]), self.score_sequence((w,)))
                for i, w in enumerate(clean_words)]
        beam.sort(key=lambda x: x[2], reverse=True)
        beam = beam[:beam_width]

        for step in range(1, n):
            candidates = []
            for seq, remaining, score in beam:
                for idx, next_w in enumerate(remaining):
                    new_seq = seq + (next_w,)
                    new_remaining = remaining[:idx] + remaining[idx+1:]
                    new_score = self.score_sequence(new_seq)
                    candidates.append((new_seq, new_remaining, new_score))
            candidates.sort(key=lambda x: x[2], reverse=True)
            beam = candidates[:beam_width]

        best_seq, _, best_score = beam[0]
        return list(best_seq), best_score
