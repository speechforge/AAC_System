import torch, time
from transformers import AutoTokenizer, AutoModelForCausalLM
from charsearch import *
name="facebook/opt-125m"
tok=AutoTokenizer.from_pretrained(name); m=AutoModelForCausalLM.from_pretrained(name,torch_dtype=torch.float16).cuda()
lm=CharSearchLM(m,tok)
for t in ["yeste","i want to g","i want ","i","", "please help m"]:
    d=lm.next_char(t); top=sorted(zip(SYMS,d),key=lambda x:-x[1])[:4]; print(repr(t),[(c,round(p,3)) for c,p in top], round(sum(d),3))
t=time.time(); lm.cache.clear(); f0=lm.n_forward
s="i need some water please"; print(lm.logp_sentence(s)/len(s), (time.time()-t)*1000/len(s),"ms/char", (lm.n_forward-f0)/len(s),"fwd/char")
