#!/usr/bin/env python3
"""OpenAlex search — permissive, no key. Primary discovery+verification channel."""
import sys, json, time, urllib.parse, urllib.request
MAIL="p2523269@mpu.edu.mo"   # polite pool
BASE="https://api.openalex.org/works"
def _get(url):
    for d in (2,4,8,16):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":f"ars-pipeline/3.22 (mailto:{MAIL})"})
            with urllib.request.urlopen(req,timeout=45) as r: return json.loads(r.read().decode())
        except Exception as e:
            err=str(e); time.sleep(d)
    return {"__error__":err}
def search(q,n=15,frm=None):
    u=f"{BASE}?search={urllib.parse.quote(q)}&per-page={n}&mailto={MAIL}"
    if frm: u+=f"&filter=from_publication_date:{frm}"
    return _get(u)
def slim(w):
    loc=(w.get("primary_location") or {}) or {}
    src=(loc.get("source") or {}) or {}
    return {"title":w.get("title"),"year":w.get("publication_year"),
            "doi":(w.get("doi") or "").replace("https://doi.org/",""),
            "venue":src.get("display_name"),"type":w.get("type"),
            "oa":(w.get("open_access") or {}).get("oa_status"),
            "cited_by":w.get("cited_by_count"),
            "authors":[a["author"]["display_name"] for a in (w.get("authorships") or [])][:5],
            "id":w.get("id","").rsplit("/",1)[-1]}
if __name__=="__main__":
    out={}
    for q in sys.argv[1:]:
        r=search(q)
        rows=[slim(w) for w in r.get("results",[])] if "__error__" not in r else r
        out[q]=rows; print(f"[{len(rows) if isinstance(rows,list) else 0:>2}] {q}",file=sys.stderr); time.sleep(1.2)
    print(json.dumps(out,ensure_ascii=False,indent=1))
