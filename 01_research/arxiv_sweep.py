#!/usr/bin/env python3
import subprocess, sys, json, xml.etree.ElementTree as ET, time
NS={'a':'http://www.w3.org/2005/Atom'}
def q(query,n=15):
    raw=subprocess.run(['./arxiv_curl.sh',query,str(n)],capture_output=True).stdout
    try: root=ET.fromstring(raw)
    except Exception: return []
    out=[]
    for e in root.findall('a:entry',NS):
        c=e.find('{http://arxiv.org/schemas/atom}comment')
        d=e.find('{http://arxiv.org/schemas/atom}doi')
        out.append({"id":e.find('a:id',NS).text.rsplit('/',1)[-1],
          "title":" ".join(e.find('a:title',NS).text.split()),
          "date":e.find('a:published',NS).text[:10],
          "authors":[a.find('a:name',NS).text for a in e.findall('a:author',NS)][:5],
          "comment":c.text.strip() if c is not None else None,
          "doi":d.text if d is not None else None,
          "abstract":" ".join(e.find('a:summary',NS).text.split())})
    return out
if __name__=="__main__":
    res={}
    for Q in sys.argv[1:]:
        res[Q]=q(Q); print(f"[{len(res[Q]):>2}] {Q}",file=sys.stderr); time.sleep(3)
    print(json.dumps(res,ensure_ascii=False,indent=1))
