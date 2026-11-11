import re
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.join(_SCRIPT_DIR, "indic-generative-aac", "frontend")

with open(os.path.join(_FRONTEND_DIR, 'index_new.html'), 'r') as f:
    text = f.read()

text = re.sub(
    r'<span class="text-3xl leading-none">\$\{s\.e\}</span><span class="text-center leading-tight">\$\{label\}</span>',
    r'<span class="text-xs font-black uppercase mb-1 w-full text-center truncate text-slate-900">${label}</span><span class="text-5xl leading-none">${s.e}</span>',
    text
)
text = re.sub(
    r'<span class="text-3xl leading-none">\$\{s\.e\}</span><span class="text-center leading-tight">\$\{s\.l\}</span>',
    r'<span class="text-xs font-black uppercase mb-1 w-full text-center truncate text-slate-900">${s.l}</span><span class="text-5xl leading-none">${s.e}</span>',
    text
)
text = re.sub(
    r'<span class="text-center w-full break-words leading-tight font-black mb-1">\$\{label\}</span><span class="text-4xl">\$\{s\.e\}</span>',
    r'<span class="text-xs font-black uppercase mb-1 w-full text-center truncate text-slate-900">${label}</span><span class="text-5xl leading-none">${s.e}</span>',
    text
)

with open(os.path.join(_FRONTEND_DIR, 'index_new.html'), 'w') as f:
    f.write(text)
