# Hindi, Gujarati and Marathi: staged extension

Keep intent and semantic roles independent of the target language. A language
switch should select a realizer and lexicon, not reinterpret what the user chose.

## Shared representation

Extend the project adapter, not the current English-only input parser, with
stable concept IDs. Preserve the original label and selection revision:

```json
{
  "language": "gu",
  "speaker_role": "USER",
  "intent": "request_object",
  "actor": "self",
  "theme": {"concept_id": "water", "label": "પાણી"},
  "action": null,
  "negation": {"present": false, "scope": null},
  "politeness": null,
  "grammatical_gender": null
}
```

`grammatical_gender` stays unknown unless supplied by the user/profile or required
by an explicitly selected referent. Prefer natural gender-neutral forms when
available. Do not choose a patient's gender from a name or a model's stereotype.

## Language-specific work

| Language | Script and realization needs | Illustrative water request |
|---|---|---|
| Hindi | Devanagari; SOV order, postpositions, agreement, honorifics, नहीं vs मत | मुझे पानी चाहिए। |
| Gujarati | Gujarati script; case/postpositions, agreement, honorifics, નથી vs નહીં in context | મને પાણી જોઈએ છે. |
| Marathi | Devanagari; agreement and postpositions, honorifics, नाही vs नको in context | मला पाणी हवे आहे. |

The examples are design illustrations, not independently validated dataset labels.
Native speakers should review training and reference sentences. Hindi and Marathi
share a script; script membership cannot identify which language was generated.

Preserve canonical negation scope and intended refusal versus factual absence.
Do not implement Indic polarity by replacing the English word `not` with one
fixed token. Store normalized Unicode text, preferably NFC for persisted labels,
and keep original forms for display. Include inflected aliases linked to concept
IDs; evaluate them with boundary-aware, language-specific rules and reviewed
semantic judgments rather than English substring matching.

## Data and model stages

1. Finish the English pilot and production intent repair first. Keep a frozen
   multilingual concept-ID schema and the English test set for regression.
2. Build native intent-template lexicons for each language. Initial collection
   goals per language can be 1,000 reviewed training pairs, 200 validation pairs
   and 200 test payloads, with all major intents and contrast pairs represented.
   These are planning quotas, not existing data or power calculations. Adjust
   them to actual inventory, review effort and observed uncertainty.
3. Draft additional pairs using [IndicTrans2](https://github.com/AI4Bharat/IndicTrans2)
   or other verified translation resources, then reconstruct the concept-to-sentence
   alignment and obtain native review. Translation alone does not produce an AAC
   intent dataset. Keep translated versions of the same semantic frame together
   for compositional-generalization tests; otherwise label any shared-frame
   cross-language transfer evaluation explicitly.
4. Compare multilingual fine-tuning of
   [mT5-small](https://huggingface.co/google/mt5-small) with the existing Qwen
   checkpoint and language-specific templates. mT5 includes Hindi, Gujarati,
   Marathi and English in pretraining, but requires downstream fine-tuning.
   Do not assume the English-tuned checkpoint already realizes these languages
   accurately. Assess tokenizer coverage, truncation, memory and script fidelity
   before selecting the multilingual model. If a shared model regresses, compare
   language-specific checkpoints/adapters within the hardware budget.
5. Train on explicit language tags, source concept IDs and native labels. Sample
   languages deliberately so English does not overwhelm smaller corpora. Record
   sampling ratios and retain English replay examples. Evaluate each language
   independently before averaging scores.
6. Add code-mixed and Romanized inputs only after native-script baselines work.
   Specify the requested output language/script and separate legitimate borrowed
   words from accidental language switching. Do not transliterate without a
   user-selected policy.

## Acceptance and rollout

Use paired bilingual concept frames, native minimal pairs, names, quantities,
honorifics, scope contrasts and deliberately ambiguous selections. Report intent,
role, negation, added-content and fallback errors separately by language. Keep
human grammaticality/adequacy separate from automatic lexical scores.

Use users/speakers as held-out groups when real interaction data become available.
Measure latency and VRAM on the deployment GPU while accounting for the existing
TTS memory load. Start with separate training/inference jobs; do not train next to
the live AAC/TTS service on a small GPU. Run a limited reviewed rollout before
changing the default language realizer. Retain raw-sentence fallback and the
current display/speak workflow throughout integration.
