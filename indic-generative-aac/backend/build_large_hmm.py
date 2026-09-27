import urllib.request
import pickle
from collections import defaultdict, Counter
import re

print("Downloading dataset...")
urls = [
    "https://www.gutenberg.org/cache/epub/11/pg11.txt", # Alice in Wonderland
    "https://www.gutenberg.org/cache/epub/16/pg16.txt", # Peter Pan
    "https://www.gutenberg.org/cache/epub/28054/pg28054.txt", # The Brothers Karamazov (Massive conversational text)
]

text = ""
for url in urls:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    text += response.read().decode('utf-8')

print("Compiling corpus...")
sentences = re.split(r'[.!?\n]', text)

bigrams = defaultdict(Counter)
trigrams = defaultdict(Counter)

def tokenize(t):
    t = t.lower()
    t = re.sub(r'[^a-z\s]', '', t)
    return t.split()

total_words = 0
for sentence in sentences:
    words = tokenize(sentence)
    if len(words) < 2: continue
    total_words += len(words)
    
    for i in range(len(words)-1):
        bigrams[words[i]][words[i+1]] += 1
    for i in range(len(words)-2):
        trigrams[(words[i], words[i+1])][words[i+2]] += 1

print(f"Trained on {total_words} words!")
print(f"Bigram states: {len(bigrams)}")
print(f"Trigram states: {len(trigrams)}")

model_path = '/home/linux/Documents/2026/aac_system_demo_track/indic-generative-aac/backend/hmm_model.pkl'
with open(model_path, 'wb') as f:
    pickle.dump({'bigrams': dict(bigrams), 'trigrams': dict(trigrams)}, f)
print(f"Saved to {model_path}!")
