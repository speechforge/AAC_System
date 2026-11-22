#!/usr/bin/env python3
"""Synthesize the 175 deployed sentences with the repository's IndicF5 engine (needs the gated weights) and add them to the MOS manifest.

The script refuses to write any clip unless the engine reports real synthesis (engine.last_audio_kind == "indicf5"), so the 440 Hz placeholder
tone can never be scored as IndicF5 speech.  The voice is the one the web client sends by default for every language (indic_female, a Punjabi
prompt); use --voice english_female for the English prompt.

Run (after the IndicF5 weights are in place):   CUDA_VISIBLE_DEVICES="" python3 -I synth_indicf5.py [--voice indic_female]
Then:  python3 -I score_mos.py && python3 -I make_mos_table.py        (the table gains one IndicF5 column per language)
"""
import argparse, pathlib, sys
import pandas as pd, soundfile as sf

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BACKEND = ROOT / "indic-generative-aac/backend"
SCORED = ROOT / "paper/CLAUDE_WRITTEN/naacl2027_demo/eval/results/scored.csv"
AUDIO = HERE / "audio"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--voice", default="indic_female"); a = ap.parse_args()
    sys.path.insert(0, str(BACKEND))
    from tts import IndicF5Engine
    eng = IndicF5Engine()
    d = pd.read_csv(SCORED)
    d = d[(d.system == "deployed") & (d.cond == "ui") & (~d.overlap) & (~d.code_mix)].reset_index(drop=True)
    assert len(d) == 175
    man = pd.read_csv(AUDIO / "manifest.csv", keep_default_na=False)
    man = man[man.group != "indicf5"]
    rows = []
    for i, r in d.iterrows():
        audio, sr = eng.generate_speech(str(r.text), lang=r.lang, code_mix=False, speaker_name=a.voice)
        if eng.last_audio_kind != "indicf5":
            raise SystemExit(f"IndicF5 did not synthesize (engine reports {eng.last_audio_kind!r}); nothing written. The weights are gated: accept the terms at huggingface.co/ai4bharat/IndicF5 first.")
        fn = f"indicf5__{r.lang}__{r['id']}.wav"
        sf.write(AUDIO / fn, audio, sr, subtype="PCM_16")
        rows.append(dict(file=fn, group="indicf5", lang=r.lang, id=r["id"], text=str(r.text)))
        if i % 20 == 0: print(i, "/ 175", flush=True)
    pd.concat([man, pd.DataFrame(rows)]).to_csv(AUDIO / "manifest.csv", index=False)
    print("added", len(rows), "IndicF5 clips")


if __name__ == "__main__":
    main()
