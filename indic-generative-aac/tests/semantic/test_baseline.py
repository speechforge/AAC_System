import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
from llm import IndicLLM

llm = IndicLLM()
context = {
    "intent": "FEELING",
    "actor": "USER",
    "entities": ["pizza"],
    "attributes": [],
    "relations": [],
    "temporal_state": "PRESENT",
    "negation": False,
    "speaker_role": "USER"
}

output = llm.generate_sentence(context, "en", False)
print("BASELINE OUTPUT:", output)
