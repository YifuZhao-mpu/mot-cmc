#!/usr/bin/env python3
"""arXiv API search -> compact records."""
import sys, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET, json
NS={'a':'http://www.w3.org/2005/Atom'}
def search(q, n=15, sort="relevance"):
    url=("https://export.arxiv.org/api/query?search_query="+urllib.parse.quote(q, safe=':')
         +f"&start=0&max_results={n}&sortBy={sort}&sortOrder=descending")
    for _ in range(4):
        try:
            req=urllib.request.Request(url, headers={"User-Agent":"ars-pipeline/3.22 (mailto:p2523269@mpu.edu.mo)"})
            with urllib.request.urlopen(req, timeout=45) as r: raw=r.read()
            break
        except Exception as e:
            time.sleep(5); raw=None
    if raw is None: return []
    root=ET.fromstring(raw); out=[]
    for e in root.findall('a:entry',NS):
        out.append({
          "id": e.find('a:id',NS).text.rsplit('/',1)[-1],
          "title":" ".join(e.find('a:title',NS).text.split()),
          "published": e.find('a:published',NS).text[:10],
          "updated": e.find('a:updated',NS).text[:10],
          "authors":[a.find('a:name',NS).text for a in e.findall('a:author',NS)][:6],
          "summary":" ".join(e.find('a:summary',NS).text.split()),
          "comment": (e.find('{http://arxiv.org/schemas/atom}comment').text
                      if e.find('{http://arxiv.org/schemas/atom}comment') is not None else None),
          "doi": (e.find('{http://arxiv.org/schemas/atom}doi').text
                  if e.find('{http://arxiv.org/schemas/atom}doi') is not None else None),
        })
    return out
if __name__=="__main__":
    res={}
    for q in sys.argv[1:]:
        res[q]=search(q); print(f"[{len(res[q]):>2}] {q}", file=sys.stderr); time.sleep(3.5)
    print(json.dumps(res,ensure_ascii=False,indent=1))
