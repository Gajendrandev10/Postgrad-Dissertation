"""Populate cached index page numbers from the latest bundled-renderer PDF."""
from pathlib import Path
import json
import re
import sys
import pdfplumber

HERE=Path(__file__).resolve().parents[3]/"Documentation/02_Dissertation/support"
report=json.loads((HERE/'build_report.json').read_text())
with pdfplumber.open(sys.argv[1]) as pdf:
    texts=[' '.join((p.extract_text() or '').split()) for p in pdf.pages]
main=next(i for i,t in enumerate(texts) if i>6 and t.startswith('Chapter 1: Introduction'))
page_map={'abstract':'i','declaration':'ii','abbreviations':'iii'}
targets=dict(report['main_headings'])
targets.update({'References':'references','Appendix A: Terms of Reference':'appendix_a','Appendix B: Ethics approval':'appendix_b','Appendix C: Digital artefact repository':'appendix_c','Appendix D: Evidence and reproduction guide':'appendix_d'})
source=(HERE/'dissertation_draft.md').read_text()
counts={'FIGURE':0,'TABLE':0}
for kind,key,cap in re.findall(r'\[\[(FIGURE|TABLE):(\w+)\|(.+)\]\]',source):
    counts[kind]+=1
    targets[kind.title()+' '+str(counts[kind])+': '+cap]=('fig_' if kind=='FIGURE' else 'tab_')+key
for text,key in targets.items():
    needle=' '.join(text.split())
    matches=[i for i in range(main,len(texts)) if needle in texts[i]]
    if len(matches)!=1:raise ValueError((text,matches))
    page_map[key]=str(matches[0]-main+1)
(HERE/'page_map.json').write_text(json.dumps(page_map,indent=2)+'\n')
print('pages',len(texts),'main starts',main+1,'mapped',len(page_map))
for i,t in enumerate(texts):
    if len(t.split())<90 and i>=main:print('short page',i+1,len(t.split()),t[:100])
