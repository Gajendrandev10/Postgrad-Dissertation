"""Figures derived from the preserved run, plus an implementation diagram."""
from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE=Path(__file__).resolve().parents[3]/"Documentation/02_Dissertation/support"
ROOT=HERE.parents[2]/"Code"
OUT=HERE/'figures'
OUT.mkdir(exist_ok=True)
RUN=ROOT/'06_Results/runs/local_only_pqc_20260906'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})

fig,ax=plt.subplots(figsize=(9,5.5));ax.set(xlim=(0,10),ylim=(0,6));ax.axis('off')
def box(x,y,w,h,txt):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.12',fc='#f2f4f6',ec='#404850'))
 ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=11)
def arrow(a,b,dashed=False):
 ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',color='#303840',lw=1.5,linestyle='--' if dashed else '-'))
box(.2,4.7,2.6,.8,'OMNeT++ generator\n494 event rows')
box(3.65,4.7,2.6,.8,'Validate and filter\n247 send records')
box(7.1,4.7,2.6,.8,'Stratified split\n172 train / 75 test')
arrow((2.95,5.1),(3.5,5.1));arrow((6.4,5.1),(6.95,5.1))
box(7.1,2.65,2.6,.9,'Train-only preparation\nIsolation Forest / RF')
arrow((8.4,4.55),(8.4,3.7))
box(3.65,2.65,2.6,.9,'Held-out predictions\n13 union-policy events')
arrow((6.95,3.1),(6.4,3.1))
box(.2,2.65,2.6,.9,'NDJSON export\nWazuh-oriented schema')
arrow((3.5,3.1),(2.95,3.1))
box(.2,.55,2.6,.9,'Wazuh collection / rules\nDelivery not verified')
arrow((1.5,2.5),(1.5,1.6),True)
box(4.4,.55,5.3,.9,'Separate local PQC demonstration\nML-KEM-768 + AES-256-GCM: 200 trials')
ax.text(5.8,1.95,'No per-event encrypted transport implemented',ha='center',fontsize=10)
fig.savefig(OUT/'architecture.png',dpi=220,bbox_inches='tight');plt.close(fig)

d=pd.read_csv(RUN/'omnet_uav_ai_dataset.csv')
fig,ax=plt.subplots(figsize=(7,4.2))
for label,marker,col,name in [(0,'o','#54758a','Normal (220)'),(1,'^','#202020','Attack (27)')]:
 q=d[d.label==label];ax.scatter(q.avg_latency_ms,q.packet_loss_pct,s=22,marker=marker,color=col,label=name,alpha=.85)
ax.set(xlabel='Generated latency attribute (ms)',ylabel='Generated packet-loss attribute (%)');ax.legend(frameon=False);ax.grid(alpha=.15)
fig.savefig(OUT/'separation.png',dpi=220,bbox_inches='tight');plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(8,3.5))
for ax,title,cm in zip(axs,['Isolation Forest','Random Forest'],[[[62,5],[0,8]],[[67,0],[0,8]]]):
 ax.imshow(cm,cmap='Blues',vmin=0,vmax=67)
 ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['Normal','Attack'],yticklabels=['Normal','Attack'],xlabel='Predicted label',ylabel='True label',title=title)
 for i in range(2):
  for j in range(2): ax.text(j,i,str(cm[i][j]),ha='center',va='center',fontsize=18,color='white' if cm[i][j]>35 else 'black')
fig.tight_layout();fig.savefig(OUT/'confusion.png',dpi=220,bbox_inches='tight');plt.close(fig)

e=json.loads((HERE/'evidence_analysis.json').read_text())
fig,ax=plt.subplots(figsize=(7,3.7));ops=list(e['pqc']);x=list(range(5))
ax.bar([i-.18 for i in x],[e['pqc'][o]['median'] for o in ops],width=.36,color='#54758a',label='Median')
ax.bar([i+.18 for i in x],[e['pqc'][o]['p95'] for o in ops],width=.36,color='#c6cdd1',edgecolor='#404040',label='95th percentile')
ax.set(xticks=x,xticklabels=['Key\ngeneration','Encapsulation','Decapsulation','AES\nencryption','AES\ndecryption'],ylabel='Local operation time (ms)');ax.legend(frameon=False);ax.grid(axis='y',alpha=.15)
fig.tight_layout();fig.savefig(OUT/'pqc.png',dpi=220,bbox_inches='tight');plt.close(fig)
print(OUT)
