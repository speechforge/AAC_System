#!/usr/bin/env python3
"""Hand-written candidate sentences with an accept/reject label per locale. DEV ONLY: they tune the gate and measure
its false acceptances/rejections on synthetic probes (written before the gate was tuned; labels are the author's, not native-checked)."""
import json, pathlib
OUT = pathlib.Path(__file__).resolve().parents[1] / "fixtures/dev/gate_probes.jsonl"
S = {  # scenario key -> (concept ids, act, negation)
    "water": (["WATER"], "REQUEST", False), "no_pizza": (["NO", "PIZZA"], "REQUEST", True), "tired": (["TIRED"], "FEELING", False),
    "no_tired": (["NO", "TIRED"], "FEELING", True), "eat_rice": (["EAT", "RICE"], "REQUEST", False)}
# (scenario, category, accept, {lang: text})
P = [
 ("water", "correct", 1, dict(en="I want water.", hi="मुझे पानी चाहिए।", gu="મને પાણી જોઈએ છે.", mr="मला पाणी हवे आहे.")),
 ("water", "implicit_first_person", 1, dict(en="Water, please.", hi="पानी चाहिए।", gu="પાણી જોઈએ છે.", mr="पाणी हवे आहे.")),
 ("water", "alternate_wording", 1, dict(en="Could I have some water?", hi="मुझे थोड़ा पानी दीजिए।", gu="મને પાણી આપો.", mr="मला पाणी द्या.")),
 ("water", "inflection_need", 1, dict(en="I need water.", hi="मुझे पानी की ज़रूरत है।", gu="મને પાણીની જરૂર છે.", mr="मला पाण्याची गरज आहे.")),
 ("no_pizza", "correct_negation", 1, dict(en="I do not want pizza.", hi="मुझे पिज़्ज़ा नहीं चाहिए।", gu="મને પિઝા નથી જોઈતો.", mr="मला पिझ्झा नको आहे.")),
 ("no_pizza", "negation_dropped", 0, dict(en="I want pizza.", hi="मुझे पिज़्ज़ा चाहिए।", gu="મને પિઝા જોઈએ છે.", mr="मला पिझ्झा हवा आहे.")),
 ("no_pizza", "negator_in_wrong_clause", 0, dict(en="I do not know. I want pizza.", hi="मुझे नहीं पता। मुझे पिज़्ज़ा चाहिए।", gu="મને ખબર નથી. મને પિઝા જોઈએ છે.", mr="मला माहीत नाही. मला पिझ्झा हवा आहे.")),
 ("water", "third_person_report", 0, dict(en="The user wants water.", hi="वह पानी चाहता है।", gu="તેને પાણી જોઈએ છે.", mr="त्याला पाणी हवे आहे.")),
 ("water", "added_reason", 0, dict(en="I want water because I am thirsty.", hi="मुझे पानी चाहिए क्योंकि मुझे प्यास लगी है।", gu="મને પાણી જોઈએ છે કારણ કે મને તરસ લાગી છે.", mr="मला पाणी हवे आहे कारण मला तहान लागली आहे.")),
 ("water", "added_time", 0, dict(en="I want water now.", hi="मुझे अभी पानी चाहिए।", gu="મને હમણાં પાણી જોઈએ છે.", mr="मला आत्ता पाणी हवे आहे.")),
 ("water", "substitution", 0, dict(en="I want milk.", hi="मुझे दूध चाहिए।", gu="મને દૂધ જોઈએ છે.", mr="मला दूध हवे आहे.")),
 ("water", "added_concept", 0, dict(en="I want water and rice.", hi="मुझे पानी और चावल चाहिए।", gu="મને પાણી અને ભાત જોઈએ છે.", mr="मला पाणी आणि भात हवा आहे.")),
 ("tired", "correct_feeling", 1, dict(en="I am tired.", hi="मुझे थकान हो रही है।", gu="મને થાક લાગ્યો છે.", mr="मला थकवा आला आहे.")),
 ("tired", "correct_feeling_alt", 1, dict(en="I feel tired.", hi="मैं थका हुआ हूँ।", gu="હું થાકેલો છું.", mr="मी दमलेला आहे.")),
 ("tired", "act_wrong_want", 0, dict(en="I want tired.", hi="मुझे थका हुआ चाहिए।", gu="મને થાકેલું જોઈએ છે.", mr="मला दमलेला हवा आहे.")),
 ("no_tired", "correct_negated_feeling", 1, dict(en="I am not tired.", hi="मुझे थकान नहीं हो रही है।", gu="મને થાક લાગ્યો નથી.", mr="मला थकवा आलेला नाही.")),
 ("no_tired", "negated_want_instead_of_feeling", 0, dict(en="I do not want tired.", hi="मुझे थका हुआ नहीं चाहिए।", gu="મને થાકેલું નથી જોઈતું.", mr="मला दमलेला नको आहे.")),
 ("water", "latin_in_indic_or_wrong_script", 0, dict(en="मुझे पानी चाहिए।", hi="Mujhe paani chahiye.", gu="Mane pani joie chhe.", mr="Mala pani have aahe.")),
 ("water", "meta_translation", 0, dict(en='The selected symbol is "water".', hi='"पानी" का मतलब water है।', gu='"પાણી" નો અર્થ water છે.', mr='"पाणी" म्हणजे water.')),
 ("eat_rice", "correct_action_object", 1, dict(en="I want to eat rice.", hi="मुझे चावल खाना है।", gu="મને ભાત જમવાનું મન છે.", mr="मला भात खाण्याची इच्छा आहे.")),
 ("eat_rice", "correct_action_object_alt", 1, dict(en="I would like to eat some rice.", hi="मैं चावल खाना चाहता हूँ।", gu="મારે ભાત ખાવા છે.", mr="मला भात खायचा आहे.")),
 ("eat_rice", "negation_spurious", 0, dict(en="I do not want to eat rice.", hi="मुझे चावल नहीं खाना है।", gu="મને ભાત જમવાનું મન નથી.", mr="मला भात खाण्याची इच्छा नाही.")),
 ("eat_rice", "action_missing", 0, dict(en="I want rice.", hi="मुझे चावल चाहिए।", gu="મને ભાત જોઈએ છે.", mr="मला भात हवा आहे.")),
]
rows = []
for sk, cat, acc, texts in P:
    ids, act, neg = S[sk]
    for lang, tx in texts.items():
        rows.append(dict(id=f"probe-{len(rows):03d}", lang=lang, scenario=sk, concept_ids=ids, act=act, negation=neg, category=cat, text=tx, gold_accept=bool(acc)))
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
print(len(rows), "probes ->", OUT)
