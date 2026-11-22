#!/usr/bin/env python3
"""Print top Crossref candidates for a title (title/authors/year/venue/DOI) so a human/agent can pick and then fetch BibTeX by DOI."""
import sys, json, urllib.request, urllib.parse
for q in sys.argv[1:]:
    url = "https://api.crossref.org/works?rows=4&select=title,author,issued,DOI,container-title,type&query.bibliographic=" + urllib.parse.quote(q)
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "paper-citation-check/1.0"}), timeout=30).read())
    except Exception as e:
        print("ERR", q, e); continue
    print("##", q)
    for it in r["message"]["items"]:
        au = "; ".join((a.get("family", "") + ", " + a.get("given", "")[:1]) for a in it.get("author", [])[:4])
        print(f"  - {it.get('title',[''])[0][:100]} | {au} | {it.get('issued',{}).get('date-parts',[[None]])[0][0]} | {it.get('container-title',[''])[0][:50]} | {it['DOI']}")
