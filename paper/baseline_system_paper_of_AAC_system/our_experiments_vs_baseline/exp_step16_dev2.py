"""Step 16 (DEV, part 2): same slot count comparison with personal vocabulary on (lam 0.1):
   8 word slots  vs  7 words + 1 phrase row (min_p 0.5 and 0.3).   python exp_step16_dev2.py lang"""
import sys, json
from lib import *
import predictor_v2 as P
import exp_step16_dev as D
lang = sys.argv[1]; m = P.LangModel(lang, sents(lang, "train"), cov=True); dev = sents(lang, "dev"); base = {}; res = {}
for name, n, ph in (("n8 personal lam0.1", 8, None), ("n7 personal lam0.1 + phrase p0.5", 7, dict(use_train=True, min_p=0.5)),
                    ("n7 personal lam0.1 + phrase p0.3", 7, dict(use_train=True, min_p=0.3)), ("n8 personal lam0.1 + phrase p0.5", 8, dict(use_train=True, min_p=0.5))):
    res[name] = round(D.run(dev, m, lang, n, 0.1, ph, base)[0], 3); print(lang, name, res[name], flush=True)
json.dump({lang: res}, open(f"results/step16_dev2_K0_{lang}.json", "w"), indent=1)
