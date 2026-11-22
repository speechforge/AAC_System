#!/usr/bin/env python3
"""Keep shaped Indic glyphs and their exact Unicode text together in XeTeX PDFs."""
from pathlib import Path
import re,json
r=Path(__file__).resolve().parents[1]
s=r/'latex_source_v3_chatgpt'
if not (s/'main.tex').exists():s=r
(r/'qa').mkdir(exist_ok=True)
strings=set()
for p in s.rglob('*.tex'):
 if p.name=='unicode_actualtext.tex':continue
 strings.update(re.findall(r'\\(?:hi|gu)\{([^{}]*)\}',p.read_text()))
strings.discard('#1')
seen={}
for x in strings:
 key=''.join(x.split())
 if key in seen and seen[key]!=x:raise ValueError('Two strings have the same control-sequence key')
 seen[key]=x
out=['% Generated from native strings in the editable section/figure/table sources.', '% UTF-16BE ActualText prevents visual-order extraction of Indic vowel signs.']
for x in sorted(strings):
 out.append('\\expandafter\\def\\csname aacunicode@'+x+'\\endcsname{'+x.encode('utf-16-be').hex().upper()+'}')
(s/'generated/unicode_actualtext.tex').write_text('\n'.join(out)+'\n')
(r/'qa/unicode_source_strings.json').write_text(json.dumps(sorted(strings),ensure_ascii=False,indent=2)+'\n')
print('Prepared exact Unicode spans for',len(strings),'native strings.')
