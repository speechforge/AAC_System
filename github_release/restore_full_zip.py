from pathlib import Path
import hashlib, json
folder = Path(__file__).resolve().parent
parts = ['Indic_AAC_Studio_CPU_Portable.zip.part01', 'Indic_AAC_Studio_CPU_Portable.zip.part02']
expected = {'Indic_AAC_Studio_CPU_Portable.zip.part01': '5986fde8e34fcf91b560e8352e254bb0ef4903e3e10721caf537afbef5fd8fce', 'Indic_AAC_Studio_CPU_Portable.zip.part02': '8073fad5a1ee41c772249bf8dbbddbb9c8fa402c53b2e81db7b9932674060ada', 'Indic_AAC_Studio_CPU_Portable.zip': '2cefcc74e7d118eeab470a7011343f21bdf84f90018a952d3f92e7efe2f44450', 'Indic_AAC_Studio_Offline_Demo.zip': '90be2558eb14a7aafdee7b5fa1e9b8f06ca1bbf7af2ffc777f08c2487037e048'}
output = folder / 'Indic_AAC_Studio_CPU_Portable.zip'
for name in parts:
    if not (folder / name).is_file():
        raise SystemExit('Download missing part: ' + name)
if output.exists():
    raise SystemExit('ZIP already exists. Move it before restoring again.')
working = output.with_suffix('.zip.tmp')
try:
    total = hashlib.sha256()
    with working.open('wb') as dest:
        for name in parts:
            part_hash = hashlib.sha256()
            with (folder / name).open('rb') as src:
                while chunk := src.read(8 * 1024 * 1024):
                    dest.write(chunk); total.update(chunk); part_hash.update(chunk)
            if part_hash.hexdigest() != expected[name]:
                raise ValueError('Corrupt download: ' + name)
    if total.hexdigest() != expected[output.name]:
        raise ValueError('Combined ZIP checksum mismatch')
    working.rename(output)
    print('Restored and verified:', output)
    print('Extract the ZIP and follow AAC_CPU_Portable/INSTALLATION_GUIDE.md')
except BaseException:
    working.unlink(missing_ok=True)
    raise
