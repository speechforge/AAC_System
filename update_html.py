import re

with open('/home/linux/Documents/2026/aac_system_demo_track/indic-generative-aac/frontend/index.html', 'r') as f:
    content = f.read()

# Add mode toggle
mode_html = """
    <!-- ── SYSTEM CONTROLS ── -->
    <section class="mt-4 flex gap-4 items-center bg-white p-4 rounded-2xl shadow-sm border border-slate-100">
      <div class="font-bold text-slate-700 text-sm mr-2">Generation Mode:</div>
      <label class="flex items-center gap-2 cursor-pointer">
        <input type="radio" name="genMode" value="single" checked class="accent-sky-500 w-4 h-4">
        <span class="text-sm font-medium text-slate-600">Single LLM (Fast)</span>
      </label>
      <label class="flex items-center gap-2 cursor-pointer">
        <input type="radio" name="genMode" value="dual" class="accent-sky-500 w-4 h-4">
        <span class="text-sm font-medium text-slate-600">Dual LLM (Quality)</span>
      </label>
      <label class="flex items-center gap-2 cursor-pointer ml-auto">
        <input type="checkbox" id="debugMode" class="accent-amber-500 w-4 h-4">
        <span class="text-sm font-bold text-amber-600">🛠 Research/Debug Mode</span>
      </label>
    </section>
    
    <!-- ── RESEARCH DEBUG PANEL ── -->
    <section id="debugPanel" class="mt-4 hidden bg-amber-50 border border-amber-200 p-4 rounded-xl text-xs font-mono text-amber-900 overflow-x-auto shadow-inner">
      <h3 class="font-bold text-sm mb-2 uppercase tracking-wide">Research Metrics & Ledger</h3>
      <pre id="debugOutput">No generation data yet...</pre>
    </section>
"""

content = content.replace('<!-- ── MAGIC CONTEXT ── -->', mode_html + '\n    <!-- ── MAGIC CONTEXT ── -->')

# Update generate() js function
gen_func_start = content.find("async function generate() {")
gen_func_end = content.find("}", content.find("audioPlayer.play();")) + 1

new_gen_func = """async function generate() {
    if(!state.intent && state.entities.length===0) return;
    const btn = document.getElementById('speakBtn');
    btn.innerHTML = '<span class="animate-spin text-xl">⏳</span> Generating...';
    btn.classList.add('opacity-75');

    const req = {
      intent: state.intent || "",
      entities: state.entities.map(e => e.l),
      language: document.getElementById('langSelect').value,
      code_mix: document.getElementById('codeMixCheck').checked,
      generation_mode: document.querySelector('input[name="genMode"]:checked').value
    };

    try {
      const res = await fetch('/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(req)
      });
      const data = await res.json();
      
      const outText = document.getElementById('outputText');
      
      if (data.validated) {
          outText.textContent = data.text;
      } else {
          outText.textContent = "[SEMANTIC VALIDATION FAILED] " + data.text;
          outText.classList.add("text-red-600");
      }

      // Update Debug Panel
      const debugPanel = document.getElementById('debugPanel');
      const debugOutput = document.getElementById('debugOutput');
      if (document.getElementById('debugMode').checked) {
          debugPanel.classList.remove('hidden');
          debugOutput.textContent = JSON.stringify(data, null, 2);
      } else {
          debugPanel.classList.add('hidden');
      }

      if(data.audio_b64) {
        const audioPlayer = document.getElementById('audioPlayer');
        audioPlayer.src = "data:audio/wav;base64," + data.audio_b64;
        audioPlayer.play();
      }
    } catch(e) {
      console.error(e);
      document.getElementById('outputText').textContent = "Error generating speech.";
    }
    
    btn.innerHTML = '🔊 Speak';
    btn.classList.remove('opacity-75');
  }"""

content = content[:gen_func_start] + new_gen_func + content[gen_func_end:]

with open('/home/linux/Documents/2026/aac_system_demo_track/indic-generative-aac/frontend/index.html', 'w') as f:
    f.write(content)

print("Updated index.html successfully.")
