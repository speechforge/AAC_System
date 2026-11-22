#!/usr/bin/env python3
"""Figure 1: system architecture. Every box maps to a file in the repository (see FINAL_CONTEXT.md, claim-to-evidence map).
Output: architecture.drawio (editable), .svg, .pdf (vector, used in the paper), .png.
Client-server arrows use dedicated lanes in the 48-unit gap between the two columns."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from diagramlib import Diagram

W, H = 800, 416
d = Diagram(W, H, "architecture")

# ---------------- groups ----------------
d.group("client", 6, 6, 168, 404, "Client: browser SPA", "group_client")
d.group("server", 222, 6, 364, 404, "Local server: FastAPI app.py", "group_server")
d.group("art", 598, 6, 196, 404, "Local artifacts", "group_art")
d.group("pred", 230, 28, 348, 68, "Prediction", "group_server")
d.group("gen", 230, 104, 348, 298, "Generation", "group_server")

# ---------------- client ----------------
d.node("c1", 14, 28, 152, 46, ["1  Symbol board", "69 symbols, 9 categories", "EN / HI / GU / MR"], "client", fs=11)
d.node("c2", 14, 84, 152, 56, ["2  Sentence canvas", "ordered concept labels", "+ intent / negation rule"], "client", fs=11)
d.node("c3", 14, 150, 152, 40, ["3  Next-word shelf", "suggestions + order"], "client", fs=11)
d.node("c4", 14, 200, 152, 56, ["4  Output card", "text, Replay, Copy,", "bookmark; plays audio"], "client", fs=11)
d.node("c5", 14, 266, 152, 40, ["localStorage cache", "prefs, My Words"], "client", fs=11)
d.node("c6", 14, 316, 152, 56, ["Web Speech API", "'Speak' voices raw labels;", "fallback if no audio"], "optional", dashed=True, fs=11)

# ---------------- prediction ----------------
d.node("s1", 236, 50, 122, 42, ["Infinity-gram trie", "EN + HI"], "model", fs=11)
d.node("s2", 364, 50, 100, 42, ["n-gram", "fallback"], "server", fs=11)
d.node("s3", 470, 50, 102, 42, ["Un-Jumble", "HMM-2 (optional)"], "optional", dashed=True, fs=11)

# ---------------- generation ----------------
d.node("g1", 246, 124, 316, 40, ["Context + concept ledger", "required and forbidden concept sets"], "server", fs=11)
d.node("g2", 246, 172, 316, 40, ["Qwen2.5-0.5B-Instruct cascade", "LLM-1 realize > LLM-2 refine > LLM-3 verify"], "model", fs=11)
d.node("g3", 246, 220, 316, 46, ["Hard validator (deterministic)", "negation, entities, forbidden, time words, intent"], "gate", fs=11)
d.node("dv", 390, 274, 80, 52, ["valid?"], "gate", shape="diamond", bold_first=False, fs=11)
d.node("g4", 246, 278, 112, 44, ["Template fallback", "after 2 rejections"], "gate", fs=10.5)
d.node("g5", 246, 346, 316, 44, ["IndicF5 DiT + Vocos, 24 kHz WAV", "mock tone when weights are absent"], "model", fs=11)

# ---------------- artifacts ----------------
d.node("a1", 606, 28, 180, 44, ["AAC dialogue JSONL", "EN + HI; builds trie at start-up"], "artifact", fs=10.5)
d.node("a4", 606, 82, 180, 44, ["HMM pickles (Git LFS)", "optional; absent in this build"], "optional", dashed=True, fs=10.5)
d.node("a2", 606, 182, 180, 44, ["Qwen2.5-0.5B weights", "HF cache or ../models"], "artifact", fs=10.5)
d.node("ext", 606, 236, 180, 100, ["Optional network services", "Firebase: sign-in + sync", "OpenAI Images: AI symbols", "Google Input Tools: translit."],
       "optional", dashed=True, fs=10.5, align="start")
d.node("a3", 606, 346, 180, 44, ["IndicF5 checkpoint +", "reference prompts"], "artifact", fs=10.5)

# ---------------- edges ----------------
d.edge("k1", [(90, 74), (90, 84)], "c1", "c2")
# prediction request / response (lanes x=182 and x=194)
d.edge("p1", [(166, 106), (182, 106), (182, 66), (236, 66)], "c2", "s1")
d.edge("p2", [(236, 82), (194, 82), (194, 170), (166, 170)], "s1", "c3")
# generation request (lane x=206) and response (lane x=200)
d.edge("r0", [(166, 126), (206, 126), (206, 144), (246, 144)], "c2", "g1")
d.edge("r1", [(404, 164), (404, 172)], "g1", "g2")
d.edge("r2", [(404, 212), (404, 220)], "g2", "g3")
d.edge("r3", [(404, 266), (404, 274)], "g3", "dv")
d.edge("r4", [(390, 300), (358, 300)], "dv", "g4", label="2nd", lpos=(374, 294), fs=10)
d.edge("r5", [(470, 300), (550, 300), (550, 192), (562, 192)], "dv", "g2", label="1st: retry", lpos=(510, 294), fs=10)
d.edge("r6", [(430, 326), (430, 346)], "dv", "g5", label="valid", lpos=(438, 340), lanchor="start", fs=10)
d.edge("r7", [(302, 322), (302, 346)], "g4", "g5")
d.edge("r8", [(246, 372), (200, 372), (200, 228), (166, 228)], "g5", "c4")
# artifacts read at start-up (dashed)
d.edge("a2e", [(606, 204), (562, 204)], "a2", "g2", dashed=True)
d.edge("a3e", [(606, 368), (562, 368)], "a3", "g5", dashed=True)
# optional client features
d.edge("x1", [(90, 306), (90, 316)], None, None, dashed=True, arrow=False)

if __name__ == "__main__":
    out = pathlib.Path(__file__).resolve().parent
    d.write(out)
    print("wrote", [p.name for p in sorted(out.glob("architecture.*"))])
