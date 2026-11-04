import emoji
import json

out = []
# EMOJI_DATA is dict of emoji -> info
for emj, info in emoji.EMOJI_DATA.items():
    if 'en' in info:
        name = info['en'].strip(':').replace('_', ' ')
        name = name.title()
        out.append({'e': emj, 'l': name, 'k': name.upper()})

js_content = "window.ALL_EMOJIS = " + json.dumps(out) + ";"
with open("/home/linux/Documents/2026/aac_system_demo_track/indic-generative-aac/frontend/all_emojis.js", "w") as f:
    f.write(js_content)
print(f"Generated all_emojis.js with {len(out)} emojis.")
