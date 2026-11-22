#!/usr/bin/env python3
"""Collect the speech samples that the MOS predictors score (UTMOS22 and NISQA v2).

Three groups, each in its own `group` column of audio/manifest.csv:
  reference    the seven voice-prompt clips that IndicF5 clones, plus the English prompt clip (real human speech)
  placeholder  the 440 Hz tone that the evaluated build returned instead of speech (regenerated with the same code as tts.py)
  standin      the 175 deployed output sentences of the frozen evaluation (scored.csv: system=deployed, cond=ui), read aloud
               by the open MMS-TTS voices (facebook/mms-tts-{eng,hin,guj,mar}), because the IndicF5 weights are gated.

Nothing here is IndicF5 output.  To add IndicF5 later, write its wav files as audio/indicf5__<lang>__<id>.wav
and add rows with group=indicf5 to the manifest (see README_MOS.md).
"""
import csv, pathlib, shutil, sys
import numpy as np, pandas as pd, soundfile as sf, torch

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
AUDIO = HERE / "audio"
SCORED = ROOT / "paper/CLAUDE_WRITTEN/naacl2027_demo/eval/results/scored.csv"
PROMPTS = ROOT / "IndicF5/prompts"
EN_PROMPT = ROOT / "IndicF5/f5_tts/infer/examples/basic/basic_ref_en.wav"
MMS = {"en": "facebook/mms-tts-eng", "hi": "facebook/mms-tts-hin", "gu": "facebook/mms-tts-guj", "mr": "facebook/mms-tts-mar"}
PROMPT_LANG = {"KAN": "kn", "MAR": "mr", "PAN": "pa", "TAM": "ta"}


def main():
    AUDIO.mkdir(exist_ok=True)
    rows = []
    # 1. reference clips (the voices IndicF5 is asked to imitate)
    for p in sorted(PROMPTS.glob("*.wav")):
        out = AUDIO / f"reference__{p.stem}.wav"
        shutil.copy(p, out)
        rows.append(dict(file=out.name, group="reference", lang=PROMPT_LANG[p.stem[:3]], id=p.stem, text=""))
    out = AUDIO / "reference__basic_ref_en.wav"
    shutil.copy(EN_PROMPT, out)
    rows.append(dict(file=out.name, group="reference", lang="en", id="basic_ref_en", text="Some call me nature, others call me mother nature."))
    # 2. the placeholder tone (same construction as backend/tts.py: 1.2 s, 440 Hz, int16, 24 kHz)
    sr = 24000
    t = np.linspace(0, 1.2, int(sr * 1.2), False)
    tone = (np.sin(440 * 2 * np.pi * t) * 32767).astype(np.int16)
    sf.write(AUDIO / "placeholder__tone.wav", tone, sr, subtype="PCM_16")
    rows.append(dict(file="placeholder__tone.wav", group="placeholder", lang="all", id="tone", text=""))
    # 3. stand-in speech for the 175 deployed sentences
    from transformers import AutoTokenizer, VitsModel
    d = pd.read_csv(SCORED)
    d = d[(d.system == "deployed") & (d.cond == "ui") & (~d.overlap) & (~d.code_mix)].reset_index(drop=True)
    assert len(d) == 175, len(d)
    dropped = {}
    for lang, name in MMS.items():
        tok = AutoTokenizer.from_pretrained(name)
        model = VitsModel.from_pretrained(name).eval()
        vocab = set(tok.get_vocab())
        sub = d[d.lang == lang]
        lost = tot = 0
        for _, r in sub.iterrows():
            text = str(r.text)
            chars = [c for c in text.lower() if not c.isspace()]
            lost += sum(c not in vocab for c in chars); tot += len(chars)
            inputs = tok(text, return_tensors="pt")
            torch.manual_seed(0)
            with torch.no_grad():
                wav = model(**inputs).waveform[0].numpy()
            fn = f"standin__{lang}__{r['id']}.wav"
            sf.write(AUDIO / fn, wav, model.config.sampling_rate, subtype="PCM_16")
            rows.append(dict(file=fn, group="standin", lang=lang, id=r["id"], text=text))
        dropped[lang] = (lost, tot)
        print(lang, name, len(sub), "sentences; characters outside the voice's vocabulary:", lost, "of", tot, flush=True)
    with open(AUDIO / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "group", "lang", "id", "text"]); w.writeheader(); w.writerows(rows)
    pd.DataFrame([dict(lang=k, lost=v[0], total=v[1]) for k, v in dropped.items()]).to_csv(HERE / "standin_vocab_loss.csv", index=False)
    print("wrote", len(rows), "rows")


if __name__ == "__main__":
    sys.exit(main())
