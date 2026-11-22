"""Rewrites the block between the FULLTABLE markers of ../20_nov_changes.md with the current output of make_full_table.py."""
import subprocess, re
tbl = subprocess.run(["python3", "make_full_table.py"], capture_output=True, text=True, check=True).stdout
md = open("../20_nov_changes.md", encoding="utf-8").read()
new = "<!-- FULLTABLE-START -->\n" + tbl + "\n<!-- FULLTABLE-END -->"
if "<!-- FULLTABLE-START -->" in md: md = re.sub(r"<!-- FULLTABLE-START -->.*?<!-- FULLTABLE-END -->", lambda m: new, md, flags=re.S)
else: raise SystemExit("markers missing")
open("../20_nov_changes.md", "w", encoding="utf-8").write(md)
