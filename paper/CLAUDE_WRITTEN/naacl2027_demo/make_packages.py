#!/usr/bin/env python3
"""Build the two submission archives from the current files.
  INDIC_AAC_NAACL2027_OVERLEAF.zip : main.tex, sections, generated numbers/tables, bibliography, official style files, compiled figures, fonts, build notes.
  INDIC_AAC_DEMO_PACKAGE.zip       : the git-tracked tree at HEAD (HMM pickles are Git LFS pointers) + this paper directory + CONTEXT.md.
Usage (from anywhere): python make_packages.py [--tectonic /path/to/tectonic]   (the clean-copy build test runs when --tectonic is given)"""
import pathlib, shutil, subprocess, sys, tempfile, zipfile
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OVERLEAF = ["main.tex", "README_BUILD.md", "acl.sty", "acl_natbib.bst", "references.bib", "build.sh"]
FIGS = ["architecture.pdf", "ui_panel.pdf", "ui_failure.pdf", "workflow.pdf"]

def zip_dir(src, out, top=None):
    out = pathlib.Path(out)
    if out.exists(): out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(pathlib.Path(src).rglob("*")):
            if p.is_file(): z.write(p, (pathlib.Path(top) / p.relative_to(src)) if top else p.relative_to(src))
    return out

def overleaf(tmp):
    d = pathlib.Path(tmp) / "overleaf"; d.mkdir()
    for f in OVERLEAF: shutil.copy(HERE / f, d / f)
    for sub in ("sections", "generated", "fonts"): shutil.copytree(HERE / sub, d / sub)
    (d / "figures").mkdir()
    for f in FIGS: shutil.copy(HERE / "figures" / f, d / "figures" / f)
    return zip_dir(d, HERE / "INDIC_AAC_NAACL2027_OVERLEAF.zip")

def package(tmp):
    d = pathlib.Path(tmp) / "pkg"; d.mkdir()
    tar = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=ROOT, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(d)], input=tar, check=True)
    ign = shutil.ignore_patterns("__pycache__", "*.zip", "main.aux", "main.log", "main.blg", "main.bbl", "*.pyc")
    shutil.copytree(HERE, d / "paper/naacl2027_demo", ignore=ign, dirs_exist_ok=True)
    if (ROOT / "CONTEXT.md").exists(): shutil.copy(ROOT / "CONTEXT.md", d / "CONTEXT.md")
    return zip_dir(d, HERE / "INDIC_AAC_DEMO_PACKAGE.zip", top="INDIC_AAC_DEMO_PACKAGE")

def clean_build(zip_path, tectonic):
    with tempfile.TemporaryDirectory() as t:
        with zipfile.ZipFile(zip_path) as z: z.extractall(t)
        r = subprocess.run([tectonic, "-X", "compile", "main.tex"], cwd=t, capture_output=True, text=True)
        pdf = pathlib.Path(t) / "main.pdf"
        pages = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout if pdf.exists() else ""
        txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout if pdf.exists() else ""
        ref = subprocess.run(["pdftotext", str(HERE / "main.pdf"), "-"], capture_output=True, text=True).stdout
        return dict(returncode=r.returncode, pages=[l for l in pages.splitlines() if l.startswith("Pages")], text_identical_to_working_build=(txt == ref))

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        o = overleaf(tmp); p = package(tmp)
    print(o.name, o.stat().st_size, "bytes |", p.name, p.stat().st_size, "bytes")
    if "--tectonic" in sys.argv:
        print("clean-copy build:", clean_build(o, sys.argv[sys.argv.index("--tectonic") + 1]))
    shutil.copy(HERE / "main.pdf", HERE / "INDIC_AAC_NAACL2027_DEMO.pdf")
