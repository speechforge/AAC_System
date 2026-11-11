import re
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.join(_SCRIPT_DIR, "indic-generative-aac", "frontend")

with open(os.path.join(_FRONTEND_DIR, 'index_new.html'), 'r', encoding='utf-8') as f:
    html = f.read()

# Remove gradients and shadows
html = re.sub(r'bg-gradient-to-[a-z]+ [^"]*', 'bg-white border-4 border-slate-800', html)
html = re.sub(r'shadow-[a-z]+', '', html)

# Convert all standard grid buttons to neutral dark borders with white background
html = re.sub(
    r"btn\.className = 'card-btn pop-in flex flex-col items-center gap-2 rounded-2xl border-2 border-slate-200 bg-white py-4 px-2 font-bold text-slate-700 text-xs shadow-sm transition-all hover:bg-sky-50 hover:border-sky-300';",
    "btn.className = 'card-btn pop-in flex flex-col items-center gap-2 rounded-lg border-4 border-slate-800 bg-white py-4 px-2 font-bold text-slate-900 text-xs transition-all hover:bg-slate-100 focus:outline-none focus:ring-4 focus:ring-blue-500';",
    html
)

html = re.sub(
    r"b\.className = 'pop-in flex items-center gap-1\.5 bg-white hover:bg-indigo-50 hover:border-indigo-400 text-indigo-900 font-bold px-3 py-1\.5 rounded-xl text-xs sm:text-sm transition-all border border-indigo-200 shadow-xs whitespace-nowrap active:scale-95 cursor-pointer';",
    "b.className = 'pop-in flex items-center gap-1.5 bg-white hover:bg-slate-100 text-slate-900 font-bold px-3 py-1.5 rounded-lg text-xs sm:text-sm transition-all border-4 border-slate-800 whitespace-nowrap focus:outline-none focus:ring-4 focus:ring-blue-500 active:scale-95 cursor-pointer';",
    html
)

# Replace sentence bar styling
html = re.sub(
    r'id="sentenceBar" class="flex flex-wrap gap-2 items-center bg-white border border-sky-100 rounded-2xl p-3 shadow-inner min-h-\[60px\]"',
    'id="sentenceBar" class="flex flex-wrap gap-2 items-center bg-white border-4 border-slate-800 rounded-lg p-3 min-h-[60px]"',
    html
)

# Intent buttons (currently purple/teal)
html = re.sub(r'border-2 border-purple-200 bg-purple-50 text-purple-700', 'border-4 border-slate-800 bg-white text-slate-900', html)
html = re.sub(r'border-2 border-teal-200 bg-teal-50 text-teal-700', 'border-4 border-slate-800 bg-white text-slate-900', html)

# Generate button (needs to be GREEN)
html = re.sub(r'bg-emerald-600 hover:bg-emerald-700', 'bg-white border-4 border-green-600 text-green-700 hover:bg-green-50 hover:border-green-700', html)
html = re.sub(r'text-white', 'text-slate-900', html) # Strip forced white text on buttons

# Stop button (needs to be RED)
html = re.sub(r'bg-rose-100 hover:bg-rose-200 text-rose-700', 'bg-white border-4 border-red-600 text-red-700 hover:bg-red-50 hover:border-red-700', html)

# Clear button (needs to be RED)
html = re.sub(r'bg-slate-100 hover:bg-slate-200 text-slate-700', 'bg-white border-4 border-red-600 text-red-700 hover:bg-red-50 hover:border-red-700', html)
html = re.sub(r'clearBtnIcon.*<span class="text-lg">🧹</span>', 'clearBtnIcon\"><span class=\"text-lg\">🗑</span>', html)

# Chip in sentence bar
html = re.sub(
    r"chip\.className = 'flex items-center gap-1\.5 bg-sky-100 text-sky-800 font-bold text-sm rounded-full px-3 py-1\.5 transition-all cursor-move';",
    "chip.className = 'flex items-center gap-1.5 bg-white text-slate-900 font-bold text-sm rounded-lg border-2 border-slate-800 px-3 py-1.5 transition-all cursor-move';",
    html
)
html = re.sub(
    r"x\.className = 'ml-1 text-sky-400 hover:text-red-500 font-black leading-none cursor-pointer';",
    "x.className = 'ml-1 text-red-600 hover:text-red-800 font-black leading-none cursor-pointer text-lg';",
    html
)

# App background
html = re.sub(r'class="bg-slate-50 text-slate-900 font-sans min-h-screen relative overflow-x-hidden pb-32 selection:bg-sky-200"', 'class="bg-white text-slate-900 font-sans min-h-screen relative overflow-x-hidden pb-32"', html)

# HMM suggestions container
html = re.sub(r'bg-gradient-to-r from-indigo-100 to-sky-100', 'bg-white border-4 border-slate-800', html)
html = re.sub(r'text-indigo-900', 'text-slate-900', html)
html = re.sub(r'text-indigo-600', 'text-slate-900', html)
html = re.sub(r'border-indigo-200', 'border-slate-800', html)
html = re.sub(r'text-sky-900', 'text-slate-900', html)
html = re.sub(r'bg-sky-50', 'bg-white', html)
html = re.sub(r'text-sky-500', 'text-blue-600', html)


with open(os.path.join(_FRONTEND_DIR, 'index_new.html'), 'w', encoding='utf-8') as f:
    f.write(html)
