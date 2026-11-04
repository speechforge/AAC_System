import json
import os
import glob
import pickle
from collections import defaultdict, Counter
import re

DATASET_DIR = "/media/linux/ShreejiPers1/Future_Conference_Works/aac_system_demo_track/hindi_AAC_Dataset"
OUTPUT_PATH = "/media/linux/ShreejiPers1/Future_Conference_Works/aac_system_demo_track/indic-generative-aac/backend/hmm_hindi.pkl"

HINDI_SYMBOL_EMOJIS = {
    "माँ": "👩", "पापा": "👨", "दादी": "👵", "दादा": "👴",
    "बहन": "👧", "भाई": "👦", "शिक्षक": "👩‍🏫", "डॉक्टर": "👨‍⚕️", "दोस्त": "👫",
    "खुश": "😊", "उदास": "😢", "गुस्सा": "😡", "थका": "😴", "बीमार": "🤒",
    "भूख": "🍽️", "प्यास": "💧", "दर्द": "😖", "पानी": "💧", "खाना": "🍎",
    "दूध": "🥛", "चावल": "🍚", "रोटी": "🍞", "फल": "🍌", "घर": "🏠",
    "स्कूल": "🏫", "अस्पताल": "🏥", "खेलना": "🎮", "पढ़ना": "📚", "सोना": "🛌",
    "जाना": "🚶", "मदद": "🆘", "दवा": "💊", "मुझे": "👤", "मैं": "👤", "तुम": "👤"
}

def clean_hindi_text(text):
    # Remove punctuation, keep Hindi characters and spaces
    text = re.sub(r'[^\u0900-\u097F\s]', ' ', text)
    words = [w.strip() for w in text.split() if w.strip()]
    return words

def build_hmm():
    priors = Counter()
    bigrams = defaultdict(Counter)
    trigrams = defaultdict(Counter)
    vocab = set()
    
    # Also inject some core AAC sequences so basic requests are always recommended
    core_seqs = [
        ["माँ"], ["पानी"], ["खाना"], ["मदद"], ["डॉक्टर"], ["थका"]
    ]
    for seq in core_seqs:
        priors[seq[0]] += 5
        vocab.update(seq)
    
    file_count = 0
    sentence_count = 0
    word_count = 0

    # Read transformed datasets
    pattern = os.path.join(DATASET_DIR, "*transformed.jsonl")
    files = glob.glob(pattern)
    print(f"Found {len(files)} transformed JSONL files.")
    
    for file_path in files:
        file_count += 1
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    # Extract conversations
                    for turn in data.get("conversation", []):
                        # We can learn from AAC user or all
                        if turn.get("is_aac_user", False):
                            text = turn.get("utterance_intended", turn.get("utterance", ""))
                        else:
                            text = turn.get("utterance", "")
                        
                        words = clean_hindi_text(text)
                        if not words: continue
                        
                        sentence_count += 1
                        word_count += len(words)
                        
                        priors[words[0]] += 1
                        for w in words:
                            vocab.add(w)
                            
                        # Bigrams
                        for i in range(len(words) - 1):
                            bigrams[words[i]][words[i+1]] += 1
                            
                        # Trigrams
                        for i in range(len(words) - 2):
                            trigrams[(words[i], words[i+1])][words[i+2]] += 1
                except json.JSONDecodeError:
                    pass

    print(f"Processed {sentence_count} sentences, {word_count} words.")
    
    # Save the model
    data_to_save = {
        "priors": dict(priors),
        "bigrams": {k: dict(v) for k, v in bigrams.items()},
        "trigrams": {k: dict(v) for k, v in trigrams.items()},
        "emojis": HINDI_SYMBOL_EMOJIS,
        "vocab": list(vocab),
        "sentence_count": sentence_count
    }

    with open(OUTPUT_PATH, 'wb') as f:
        pickle.dump(data_to_save, f)

    print(f"Successfully trained Hindi AAC HMM on dataset!")
    print(f"Saved to {OUTPUT_PATH}")
    print(f"Vocabulary: {len(vocab)} symbols | Bigram transitions: {len(bigrams)} | Trigrams: {len(trigrams)}")

if __name__ == "__main__":
    build_hmm()
