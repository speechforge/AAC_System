# Speech-quality (UTMOS22 and NISQA v2) evaluation of the speech samples

Result: Table 8 of the paper (Appendix B), built from `mos_scores.csv` by `make_mos_table.py`.

## What was scored, and what was not

| Group | Clips | What it is |
|---|---|---|
| `placeholder` | 1 | The 440 Hz tone that the evaluated build returned for every sentence (regenerated with the same code as `backend/tts.py`; every `audio_b64_len` in `raw_pipeline.jsonl` is 76,860, i.e. 1.2 s at 24 kHz) |
| `reference` | 8 | The voice-prompt clips of the repository (`IndicF5/prompts/*.wav`, `basic_ref_en.wav`): the voices IndicF5 is asked to imitate. The default for every language is the Punjabi clip `PAN_F_HAPPY_00001` |
| `standin` | 175 | The 175 deployed sentences of the frozen evaluation (`scored.csv`: system `deployed`, condition `ui`, no overlap, no code-mix), read by the open MMS-TTS voices (`facebook/mms-tts-{eng,hin,guj,mar}`, CC BY-NC 4.0) because the IndicF5 weights are gated |
| `indicf5` | 0 | **Not run.** `synth_indicf5.py` produces these once the weights are available |

**None of the numbers describes IndicF5.** The stand-in rows measure the open MMS voices (a check that the scoring pipeline works on the four languages and a rough anchor between a tone and human speech), not the system's speech.

Predictors: UTMOS22 strong (`speechmos.utmos22`, checkpoint `utmos22_strong_step7459_v1.pt`, 16 kHz) and NISQA v2 (`nisqa.tar`, Mittag's code in `predict_dir` mode). Both run on the CPU. Both are trained on English-language ratings, so the values for Hindi, Gujarati, and Marathi are indicative only, and NISQA scores signal quality (noise, coloration, discontinuity), not naturalness or intelligibility (it gives 4.9 to the Gujarati stand-in voice and 3.5 to the Hindi one; read that as a property of the two voices). Pearson r between the two predictors over the 175 stand-in clips: 0.47. No listening test was run; no native-speaker ratings exist.

Lost characters: the MMS tokenizers drop characters outside their vocabulary: full stops, commas, the danda (every sentence), and the vowel signs ૉ (2) and ॉ (2) in Gujarati and Marathi (`standin_vocab_loss.csv`).

## Re-running

```
python3 -I build_audio.py       # reference clips, tone, MMS stand-in clips (needs network once for the MMS weights)
python3 -I score_mos.py         # UTMOS22 + NISQA v2 -> mos_scores.csv
python3 -I make_mos_table.py    # -> ../latex_source_v3/generated/tab_mos.tex and mos.tex
python3 -I check_mos.py         # independent recount of every table cell
```

Paths inside the scripts assume this repository layout and the vendored NISQA copy at
`/home/linux/Documents/Future_Conference_2026/ICASSP_2027/Vocoder_benchmarking/English_Vocoder_Analysis_2027_ICASSP/third_party/NISQA` (`--nisqa-root` overrides it).

## Adding IndicF5 speech (what the table is waiting for)

1. Accept the terms at huggingface.co/ai4bharat/IndicF5 with the account used on this machine, and install the `f5_tts` package from `IndicF5/`.
2. `CUDA_VISIBLE_DEVICES="" python3 -I synth_indicf5.py` (it refuses to write a clip unless the engine reports real synthesis, so the placeholder tone cannot be scored as IndicF5 speech; tested: with the weights absent it writes nothing).
3. Re-run `score_mos.py`, `make_mos_table.py`, `check_mos.py`; the table gains one IndicF5 column per language. Then edit the Appendix B sentence ("\indicf{} ... not run"), the Limitations sentence, the abstract's "no speech was produced", and the page budget (the appendix has about 3 spare lines).

Note for the authors' other project: in `English_Vocoder_Analysis_2027_ICASSP/calc_nisqa.py`, `nisqaModel` has no `predict_file` method (the call sits in a bare `except` and returns NaN), and `calc_neural.py` calls `speechmos.utmos.score`, which does not exist in the installed package (also NaN); `score_mos.py` here shows a working route for both.
