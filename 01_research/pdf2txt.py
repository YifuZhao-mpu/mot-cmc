#!/usr/bin/env python3
import sys, fitz
doc = fitz.open(sys.argv[1])
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 1
hi = int(sys.argv[3]) if len(sys.argv) > 3 else doc.page_count
for i in range(lo-1, min(hi, doc.page_count)):
    print(f"\n===== p{i+1} =====")
    print(doc[i].get_text())
