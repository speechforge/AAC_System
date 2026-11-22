#!/usr/bin/env python3
"""Score every clip listed in audio/manifest.csv with UTMOS22 (strong) and NISQA v2 and write mos_scores.csv.

UTMOS22: speechmos.utmos22 re-implementation, checkpoint utmos22_strong_step7459_v1.pt (clip resampled to 16 kHz).
NISQA v2: Mittag's reference code (vendored copy) with weights/nisqa.tar, run in predict_dir mode (the official route).
Both run on the CPU.  Both predictors were trained on English-language MOS data, so their values for Hindi, Gujarati,
and Marathi speech are indicative only and are not a listening test.

Run:  python3 -I score_mos.py [--nisqa-root DIR]
"""
import argparse, os, pathlib, subprocess, sys, tempfile
import librosa, pandas as pd, torch

HERE = pathlib.Path(__file__).resolve().parent
AUDIO = HERE / "audio"
DEFAULT_NISQA = pathlib.Path("/home/linux/Documents/Future_Conference_2026/ICASSP_2027/Vocoder_benchmarking/English_Vocoder_Analysis_2027_ICASSP/third_party/NISQA")
UTMOS_CKPT = pathlib.Path.home() / ".cache/torch/hub/checkpoints/utmos22_strong_step7459_v1.pt"


def utmos(files):
    from speechmos.utmos22.strong.model import UTMOS22Strong
    m = UTMOS22Strong(); m.load_state_dict(torch.load(UTMOS_CKPT, map_location="cpu")); m.eval()
    out = []
    for i, f in enumerate(files):
        y, sr = librosa.load(AUDIO / f, sr=16000)
        with torch.no_grad():
            out.append(float(m(torch.from_numpy(y).unsqueeze(0), sr)))
        if i % 40 == 0: print("UTMOS22", i, "/", len(files), flush=True)
    return out


def nisqa(root, files):
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [sys.executable, "run_predict.py", "--mode", "predict_dir", "--pretrained_model", str(root / "weights/nisqa.tar"),
               "--data_dir", str(AUDIO), "--output_dir", tmp, "--num_workers", "0", "--bs", "1"]
        env = dict(os.environ, CUDA_VISIBLE_DEVICES="")
        r = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True)
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-2000:]); raise SystemExit("NISQA failed")
        res = pd.read_csv(pathlib.Path(tmp) / "NISQA_results.csv")
    res = res.rename(columns={"deg": "file", "mos_pred": "nisqa_mos", "noi_pred": "nisqa_noi", "dis_pred": "nisqa_dis", "col_pred": "nisqa_col", "loud_pred": "nisqa_loud"})
    res["file"] = res["file"].map(lambda s: pathlib.Path(s).name)
    return res[["file", "nisqa_mos", "nisqa_noi", "nisqa_dis", "nisqa_col", "nisqa_loud"]]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--nisqa-root", default=str(DEFAULT_NISQA)); a = ap.parse_args()
    man = pd.read_csv(AUDIO / "manifest.csv", keep_default_na=False)
    man["duration_s"] = [round(librosa.get_duration(path=str(AUDIO / f)), 3) for f in man.file]
    man["utmos"] = utmos(list(man.file))
    n = nisqa(pathlib.Path(a.nisqa_root), list(man.file))
    out = man.merge(n, on="file", how="left")
    assert out.nisqa_mos.notna().all(), out[out.nisqa_mos.isna()].file.tolist()
    out.to_csv(HERE / "mos_scores.csv", index=False)
    print(out.groupby(["group", "lang"])[["utmos", "nisqa_mos"]].agg(["count", "mean", "std"]).round(2).to_string())


if __name__ == "__main__":
    main()
