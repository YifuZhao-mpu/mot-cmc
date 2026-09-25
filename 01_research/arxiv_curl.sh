#!/bin/bash
# $1 = raw arXiv search_query, $2 = max_results
q=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=':'))" "$1")
curl -sS --max-time 60 "https://export.arxiv.org/api/query?search_query=${q}&start=0&max_results=${2:-15}&sortBy=relevance&sortOrder=descending"
