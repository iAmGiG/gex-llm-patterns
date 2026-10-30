import sqlite3, json, re, yaml, collections
import numpy as np
con=sqlite3.connect("file:.cache/gex_database.db?mode=ro",uri=True)
rows=con.execute("select date,spot_price,total_gex,net_call_gex,net_put_gex,options_count from daily_gex_metrics where symbol='SPY' and date like '2024%' order by date").fetchall()
db={r[0]:r for r in rows}
real=[r for r in rows if r[3]!=0 or r[4]!=0]
print("real",len(real))
rel=[(r[2]/(r[3]+r[4])) for r in real]
print("total/(c+p) ratio min/max",min(rel),max(rel))
d=[abs(r[2]+(r[3]+r[4])) for r in real]
print("max |total+(c+p)|",max(d), "max |total|",max(abs(r[2]) for r in real))
print("signs c,p real", sum(r[3]<0 for r in real), sum(r[4]<0 for r in real), "total<0",sum(r[2]<0 for r in real))
PH=[r[0] for r in rows if r[3]==0 and r[4]==0]
print("PH",PH)
# jsonl
wins={}
for l in open("reports/validation/paper2_regime_windows/batch_jobs/phase3_full_2024_baseline_v2.jsonl"):
    j=json.loads(l); c=j['body']['messages'][0]['content']
    vals=re.findall(r'^(\d{4}-\d{2}-\d{2}): ([+-]?[\d.]+)B',c,re.M)
    wins[j['custom_id']]=vals
print("n windows",len(wins), set(len(v) for v in wins.values()))
neg=pos=0; mism=0; allv={}
for k,v in wins.items():
    for dt,x in v:
        x=float(x); allv[dt]=x
        if x<0: neg+=1
        else: pos+=1
print("window-values neg/pos",neg,pos)
print("unique dates",len(allv),"neg dates",sum(x<0 for x in allv.values()),"pos dates",[d for d,x in allv.items() if x>0])
# compare with db
mx=0
for dt,x in allv.items():
    mx=max(mx,abs(x-db[dt][2]/1e9))
print("max abs diff jsonl vs db (B)",mx)
y=yaml.safe_load(open("reports/validation/paper2_regime_windows/phase3_baseline_2024_full_year.yaml"))
W=y['windows']; print(W[0].keys())
lab={w['window_id']:w for w in W}
print(len(W), collections.Counter(w['regime_type'] for w in W))
cnt=collections.Counter(); 
rej=[];det=[]
for k,v in wins.items():
    n=sum(1 for dt,x in v if dt in PH)
    w=lab.get(k)
    if w is None: print('missing',k); continue
    isdet = w.get('regime_detected', w['regime_type'] in('persistent_negative','persistent_positive'))
    (det if isdet else rej).append(n)
print("rejected n",len(rej),"placeholders per rej",collections.Counter(rej))
print("detected n",len(det),"placeholders per det",collections.Counter(det))
