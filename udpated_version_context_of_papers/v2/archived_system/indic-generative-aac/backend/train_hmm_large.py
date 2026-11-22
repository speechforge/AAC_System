"""
train_hmm_large.py
Downloads 100K+ English sentences from Project Gutenberg + NLTK
and trains a bigram/trigram model, saving to hmm_model.pkl.
"""
import pickle, re, os, urllib.request
from collections import defaultdict, Counter

OUTPUT = os.path.join(os.path.dirname(__file__), 'hmm_model.pkl')

# ── Gutenberg book IDs to download ─────────────────────────────────────
GUTENBERG_IDS = [
    1342, 84, 1661, 2701, 11, 74, 76, 1232, 2591, 2554,
    98,   1260, 345, 46, 1400, 5200, 25344, 2600, 4300, 6130,
    35,   36,   37,  100, 1184, 2097, 174,   244,  514,  863,
    1080, 1251, 1399, 1952, 2148, 2413, 2814, 3207, 3296, 4517,
    4683, 5765, 7370, 8164, 11231, 16328, 20213, 23042, 27827, 30254
]

def fetch_gutenberg(book_id):
    urls = [
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read().decode('utf-8', errors='ignore')
                # Strip Gutenberg header/footer
                start = raw.find('*** START')
                end   = raw.find('*** END')
                if start > 0: raw = raw[start+100:]
                if end   > 0: raw = raw[:end]
                return raw
        except Exception:
            continue
    return ""

def text_to_sentences(text):
    # Split on sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    out = []
    for s in sentences:
        s = s.strip()
        if 10 < len(s) < 300:
            # Clean: remove non-alpha except spaces
            s = re.sub(r'[^a-zA-Z\s]', '', s).lower().strip()
            words = s.split()
            if 3 <= len(words) <= 40:
                out.append(words)
    return out

def train(sentences):
    bigrams  = defaultdict(Counter)
    trigrams = defaultdict(Counter)
    for words in sentences:
        for i in range(len(words)-1):
            bigrams[words[i]][words[i+1]] += 1
        for i in range(len(words)-2):
            trigrams[(words[i], words[i+1])][words[i+2]] += 1
    return bigrams, trigrams

# ── Main ────────────────────────────────────────────────────────────────
print("Starting HMM training on 100K+ sentences from Project Gutenberg...")
all_sentences = []
success = 0

for idx, book_id in enumerate(GUTENBERG_IDS):
    try:
        text = fetch_gutenberg(book_id)
        if not text:
            print(f"  [{idx+1}/{len(GUTENBERG_IDS)}] Book {book_id}: SKIP (no content)")
            continue
        sents = text_to_sentences(text)
        all_sentences.extend(sents)
        success += 1
        print(f"  [{idx+1}/{len(GUTENBERG_IDS)}] Book {book_id}: +{len(sents)} sentences (total={len(all_sentences)})")
        if len(all_sentences) >= 150000:
            print("  Reached 150K sentences — stopping early.")
            break
    except Exception as e:
        print(f"  [{idx+1}/{len(GUTENBERG_IDS)}] Book {book_id}: ERROR {e}")

print(f"\nTotal sentences collected: {len(all_sentences)} from {success} books")

if len(all_sentences) < 1000:
    print("ERROR: Too few sentences collected. Check network connection.")
    exit(1)

print("Training bigram/trigram model...")
bigrams, trigrams = train(all_sentences)
print(f"  Bigram states:  {len(bigrams):,}")
print(f"  Trigram states: {len(trigrams):,}")

print(f"Saving model to {OUTPUT}...")
with open(OUTPUT, 'wb') as f:
    pickle.dump({'bigrams': bigrams, 'trigrams': trigrams, 'sentence_count': len(all_sentences)}, f)

print(f"Done! HMM model saved with {len(all_sentences):,} training sentences.")
