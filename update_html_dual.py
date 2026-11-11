import re

with open('/home/linux/Documents/2026/aac_system_demo_track/indic-generative-aac/frontend/index.html', 'r') as f:
    content = f.read()

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
      outText.classList.remove("text-red-600");
      outText.innerHTML = "";
      
      let displayText = "";
      
      if (data.mode === "dual" && data.candidate_llm1) {
          displayText += `<div class="mb-2 text-sm text-slate-500 font-semibold uppercase tracking-wider">LLM-1 (Candidate):</div>`;
          displayText += `<div class="mb-4 text-slate-400 line-through">${data.candidate_llm1}</div>`;
          displayText += `<div class="mb-2 text-sm text-indigo-600 font-semibold uppercase tracking-wider">LLM-2 (Merged/Refined Sentence):</div>`;
      }
      
      if (data.validated) {
          displayText += `<div class="font-bold text-slate-800">${data.text}</div>`;
      } else {
          displayText += `<div class="font-bold text-red-600">[SEMANTIC VALIDATION FAILED] ${data.text}</div>`;
      }
      
      outText.innerHTML = displayText;

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
      document.getElementById('outputText').innerHTML = "<div class='text-red-600 font-bold'>Error generating speech.</div>";
    }
    
    btn.innerHTML = '🔊 Speak';
    btn.classList.remove('opacity-75');
  }"""

content = content[:gen_func_start] + new_gen_func + content[gen_func_end:]

with open('/home/linux/Documents/2026/aac_system_demo_track/indic-generative-aac/frontend/index.html', 'w') as f:
    f.write(content)

print("Updated index.html successfully.")
