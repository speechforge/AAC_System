import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

device = "cuda"
model_id = "Qwen/Qwen2.5-0.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16).to(device)

prompt = """Generate a JSON object containing 4 AAC intents and 10 AAC symbols for a child based on context: morning routine.
Format exactly as this JSON structure:
{
  "intents": [
    {"intent": "REQUEST", "emoji": "🤲", "label": "I want"},
    {"intent": "STATEMENT", "emoji": "💬", "label": "I feel"}
  ],
  "symbols": [
    {"id": "WATER", "emoji": "💧", "label": "Water"},
    {"id": "HAPPY", "emoji": "😊", "label": "Happy"}
  ]
}
Output ONLY valid JSON."""

messages = [{"role": "system", "content": "You are an AI assistant that only outputs valid JSON without markdown formatting."}, {"role": "user", "content": prompt}]
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
model_inputs = tokenizer([text], return_tensors="pt").to(device)
with torch.no_grad():
    generated_ids = model.generate(**model_inputs, max_new_tokens=300, temperature=0.3)
generated_ids = [out[len(inp):] for inp, out in zip(model_inputs.input_ids, generated_ids)]
print(tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0])
