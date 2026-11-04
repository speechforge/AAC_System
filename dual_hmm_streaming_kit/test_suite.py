"""
test_suite.py - Clinical & Conversational AAC Benchmark Test Suite
Used to evaluate Next-Word Prediction Accuracy and Syntactic Un-Jumbling Exact Match.
"""

AAC_EVAL_SENTENCES = [
    # Basic Needs
    "i want to drink water",
    "please give me cold water",
    "i am very hungry now",
    "i want to eat food",
    "can i have some food please",
    "i need to go to bathroom",
    
    # Medical & Comfort
    "i have severe pain",
    "please call the doctor now",
    "i need to take my medicine",
    "my head is hurting very badly",
    "i am feeling very sick today",
    "i need help immediately",
    
    # Social & Conversational
    "hello how are you doing",
    "thank you very much for your help",
    "can you please help me",
    "i want to speak with you",
    "what time is it now",
    "where are we going today",
    
    # Emotional & State
    "i am feeling very tired",
    "i want to go to sleep",
    "i am very happy today",
    "i do not like this",
    "please do not do that",
    "i love you so much"
]

def get_next_word_test_cases():
    """
    Generate test cases (prefix_tokens, expected_next_word)
    """
    cases = []
    for s in AAC_EVAL_SENTENCES:
        words = s.lower().split()
        for i in range(1, len(words)):
            prefix = words[:i]
            target = words[i]
            cases.append((prefix, target))
    return cases

def get_unjumble_test_cases():
    """
    Generate test cases (jumbled_tokens, canonical_tokens)
    """
    import random
    rng = random.Random(42)
    cases = []
    for s in AAC_EVAL_SENTENCES:
        canonical = s.lower().split()
        if len(canonical) >= 3:
            # Create deterministic permutation
            jumbled = list(canonical)
            while jumbled == canonical:
                rng.shuffle(jumbled)
            cases.append((jumbled, canonical))
    return cases
