import sys
from llm import IndicLLM

print("Testing LLM...")
llm = IndicLLM()
ctx = {"intent": "REQUEST", "entities": ["water"]}
res, *_ = llm.generate_sentence(ctx, language="hi")
print("Hindi:", res)
res, *_ = llm.generate_sentence(ctx, language="hi", code_mix=True)
print("Hinglish:", res)
res, *_ = llm.generate_sentence(ctx, language="gu")
print("Gujarati:", res)
