#!/usr/bin/env python3
"""Semantic Scholar Graph API search with backoff. Tier-0 verification per ARS protocol."""
import json, sys, time, urllib.parse, urllib.request, os

BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,authors,year,externalIds,venue,publicationDate,citationCount,abstract,openAccessPdf"
KEY = os.environ.get("S2_API_KEY")

def _get(url, tries=6):
    hdr = {"User-Agent": "ars-pipeline/3.22"}
    if KEY:
        hdr["x-api-key"] = KEY
    delay = 2.0
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=hdr)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(delay); delay = min(delay * 1.8, 30); continue
            return {"__error__": f"HTTP {e.code}"}
        except Exception as e:
            time.sleep(delay); delay = min(delay * 1.8, 30)
    return {"__error__": "exhausted retries"}

def search(q, limit=8):
    url = f"{BASE}/paper/search?query={urllib.parse.quote(q)}&limit={limit}&fields={FIELDS}"
    return _get(url)

if __name__ == "__main__":
    queries = [l.strip() for l in sys.argv[1:] if l.strip()]
    out = {}
    for q in queries:
        r = search(q)
        out[q] = r.get("data", []) if "__error__" not in r else r
        n = len(out[q]) if isinstance(out[q], list) else 0
        print(f"[{n:>2}] {q}", file=sys.stderr)
        time.sleep(3.5)
    print(json.dumps(out, ensure_ascii=False, indent=1))
