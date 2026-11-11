import re

with open('/media/linux/ShreejiPers1/Future_Conference_Works/aac_system_demo_track/indic-generative-aac/frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Reset Body Background
html = re.sub(
    r'<body class="bg-gradient-to-[^"]*"',
    '<body class="bg-white text-slate-900 min-h-screen"',
    html
)

# 2. Make all vocabulary/intent/category buttons Neutral (White + Dark Border)
# The intent buttons
html = re.sub(r'border-[a-z]+-\d+ bg-[a-z]+-\d+ text-[a-z]+-\d+ (intent-btn|cat-tab)', 'border-4 border-slate-800 bg-white text-slate-900 \\1', html)
html = re.sub(r'intent-btn.*border-2', 'intent-btn flex flex-col items-center gap-1.5 rounded-lg border-4 border-slate-800 bg-white py-5 font-bold text-slate-900 transition-all hover:bg-slate-100', html)

# The category tabs
html = re.sub(
    r'cat-tab.*bg-[a-z]+-\d+ text-[a-z]+-\d+.*border-[a-z]+-\d+',
    'cat-tab shrink-0 rounded-lg bg-white text-slate-900 font-bold text-xs px-4 py-2 border-4 border-slate-800 transition-all hover:bg-slate-100',
    html
)
# Fix hover rings on categories
html = re.sub(r'ring-sky-400', 'ring-blue-600', html)

# 3. Sentence Bar & Chips
html = re.sub(
    r'id="sentenceBar" class="flex flex-wrap gap-2 items-center bg-white border border-[^"]*"',
    'id="sentenceBar" class="flex flex-wrap gap-2 items-center bg-white border-4 border-slate-800 rounded-lg p-3 min-h-[60px]"',
    html
)

# 4. Generate Button -> GREEN Confirm
html = re.sub(
    r'id="genBtn" onclick="generate\(\)" class="bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-bold rounded-2xl px-6 py-4 shadow-sm transition-all flex items-center gap-3 shrink-0"',
    'id="genBtn" onclick="generate()" class="bg-white hover:bg-green-100 border-4 border-green-600 text-green-700 font-bold rounded-lg px-6 py-4 transition-all flex items-center gap-3 shrink-0 focus:ring-4 focus:ring-green-400"',
    html
)
# Ensure icon checkmark instead of wand or keep text?
# The prompt says: GREEN + ✓ + "YES" or "Confirm"
html = re.sub(r'<span id="genBtnIcon" class="text-2xl">✨</span>', '<span id="genBtnIcon" class="text-2xl font-black">✓</span>', html)

# 5. Clear Button -> RED Delete
html = re.sub(
    r'id="clearBtn".*bg-slate-100 hover:bg-slate-200 active:scale-95 text-slate-700 font-bold rounded-2xl px-6 py-4 shadow-sm transition-all flex items-center gap-2"',
    'id="clearBtn" onclick="clearAll()" class="bg-white hover:bg-red-100 border-4 border-red-600 text-red-700 font-bold rounded-lg px-6 py-4 transition-all flex items-center gap-2 focus:ring-4 focus:ring-red-400"',
    html
)
html = re.sub(r'<span id="clearBtnIcon" class="text-lg">🧹</span>', '<span id="clearBtnIcon" class="text-xl font-black">🗑</span>', html)

# 6. Stop Audio Button -> RED Stop
html = re.sub(
    r'id="stopBtn".*bg-rose-100 hover:bg-rose-200 active:scale-95 text-rose-700 font-bold rounded-2xl px-5 py-3 shadow-sm transition-all flex items-center gap-2"',
    'id="stopBtn" onclick="stopAudio()" class="bg-white hover:bg-red-100 border-4 border-red-600 text-red-700 font-bold rounded-lg px-5 py-3 transition-all flex items-center gap-2 focus:ring-4 focus:ring-red-400"',
    html
)
html = re.sub(r'<span class="text-xl">🛑</span>', '<span class="text-xl font-black">✕</span>', html)

# 7. JavaScript Dynamic Classes Updates

# updatePredictions: HMM recommendations grid -> White cell, dark border
html = re.sub(
    r"btn\.className = 'card-btn pop-in flex flex-col items-center gap-2 rounded-2xl border-2 border-slate-200 bg-white py-4 px-2 font-bold text-slate-700 text-xs shadow-sm transition-all hover:bg-sky-50 hover:border-sky-300';",
    "btn.className = 'card-btn pop-in flex flex-col items-center gap-2 rounded-lg border-4 border-slate-800 bg-white py-4 px-2 font-bold text-slate-900 text-sm transition-all hover:bg-slate-100 focus:outline-none focus:ring-4 focus:ring-blue-500';",
    html
)

# showCat: Standard vocabulary cells -> White cell, dark border
html = re.sub(
    r"btn\.className = 'card-btn pop-in flex flex-col items-center gap-2 rounded-2xl border-2 border-slate-200 bg-white py-4 px-2 font-bold text-slate-700 text-xs shadow-sm transition-all hover:bg-sky-50 hover:border-sky-300';",
    "btn.className = 'card-btn pop-in flex flex-col items-center gap-2 rounded-lg border-4 border-slate-800 bg-white py-4 px-2 font-bold text-slate-900 text-sm transition-all hover:bg-slate-100 focus:outline-none focus:ring-4 focus:ring-blue-500';",
    html
)

# addChip: Selected words in sentence bar -> Neutral/Blue border? 
# "Standard communication symbols -> dark border"
html = re.sub(
    r"chip\.className = 'flex items-center gap-1\.5 bg-sky-100 text-sky-800 font-bold text-sm rounded-full px-3 py-1\.5 transition-all cursor-move';",
    "chip.className = 'flex items-center gap-1.5 bg-white text-slate-900 font-bold text-sm rounded-lg border-4 border-slate-800 px-3 py-1.5 transition-all cursor-move';",
    html
)

# addChip close button -> RED
html = re.sub(
    r"x\.className = 'ml-1 text-sky-400 hover:text-red-500 font-black leading-none cursor-pointer';",
    "x.className = 'ml-1 text-red-600 hover:text-red-800 font-black text-xl leading-none cursor-pointer';",
    html
)

# 8. Remove redundant background gradient classes inside recommendationContainer
html = re.sub(
    r'id="recommendationContainer" class="hidden bg-gradient-to-r from-[^"]*"',
    'id="recommendationContainer" class="hidden bg-white border-4 border-slate-800 mt-4 p-3 rounded-lg"',
    html
)

# 9. Structure of Cell: LABEL above SYMBOL
# We'll reorder the innerHTML in `addChip`, `showCat`, `updatePredictions`
# In `showCat` and `updatePredictions` it was:
# `<span class="text-3xl">${s.e}</span><span class="text-center w-full break-words leading-tight">${label}</span>`
html = re.sub(
    r'`<span class="text-3xl">\$\{s\.e\}</span><span class="text-center w-full break-words leading-tight">\$\{label\}</span>`',
    '`<span class="text-center w-full break-words leading-tight font-black mb-1">${label}</span><span class="text-4xl">${s.e}</span>`',
    html
)
html = re.sub(
    r'`<span class="text-3xl">\$\{s\.e\}</span><span class="text-center w-full break-words leading-tight">\$\{label\}</span>`',
    '`<span class="text-center w-full break-words leading-tight font-black mb-1">${label}</span><span class="text-4xl">${s.e}</span>`',
    html
)
# For `showCat`:
html = re.sub(
    r'`<span class="text-3xl">\$\{s\.e\}</span><span class="text-center w-full break-words leading-tight">\$\{label\}</span>`',
    '`<span class="text-center w-full break-words leading-tight font-black mb-1">${label}</span><span class="text-4xl">${s.e}</span>`',
    html
)

# 10. Make sure all category tabs have dark borders and no specialized bg colors
html = re.sub(r'bg-pink-100 text-pink-700 border-pink-200 hover:bg-pink-200', 'bg-white text-slate-900 border-slate-800 hover:bg-slate-100', html)
html = re.sub(r'bg-rose-100 text-rose-700 border-rose-200 hover:bg-rose-200', 'bg-white text-slate-900 border-slate-800 hover:bg-slate-100', html)
html = re.sub(r'bg-green-100 text-green-700 border-green-200 hover:bg-green-200', 'bg-white text-slate-900 border-slate-800 hover:bg-slate-100', html)
html = re.sub(r'bg-blue-100 text-blue-700 border-blue-200 hover:bg-blue-200', 'bg-white text-slate-900 border-slate-800 hover:bg-slate-100', html)
html = re.sub(r'bg-yellow-100 text-yellow-700 border-yellow-200 hover:bg-yellow-200', 'bg-white text-slate-900 border-slate-800 hover:bg-slate-100', html)
html = re.sub(r'bg-purple-100 text-purple-700 border-purple-200 hover:bg-purple-200', 'bg-white text-slate-900 border-slate-800 hover:bg-slate-100', html)
html = re.sub(r'bg-red-100 text-red-700 border-red-200 hover:bg-red-200', 'bg-white text-slate-900 border-slate-800 hover:bg-slate-100', html)
html = re.sub(r'bg-indigo-100 text-indigo-700 border-indigo-200 hover:bg-indigo-200', 'bg-white text-slate-900 border-slate-800 hover:bg-slate-100', html)
html = re.sub(r'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200', 'bg-white text-slate-900 border-slate-800 hover:bg-slate-100', html)

# 11. Suggest box transliteration hint -> blue borders, not magical gradients
html = re.sub(
    r'bg-gradient-to-r from-indigo-50/70 via-sky-50/50 to-indigo-50/70',
    'bg-white border-4 border-blue-600',
    html
)
html = re.sub(
    r'border-indigo-100/80',
    '',
    html
)
html = re.sub(
    r'bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white',
    'bg-white border-4 border-blue-600 text-blue-700 hover:bg-blue-50',
    html
)

# Change text size of label on genBtn to match prompt emphasis
html = re.sub(r'id="genBtnText" class="text-sm"', 'id="genBtnText" class="text-lg font-black"', html)

with open('/media/linux/ShreejiPers1/Future_Conference_Works/aac_system_demo_track/indic-generative-aac/frontend/index_new.html', 'w', encoding='utf-8') as f:
    f.write(html)
