import json,re,sqlite3,yaml,numpy as np,pandas as pd,collections
B='/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns/'
raw=pd.read_csv('v2_raw_2024.csv'); p=raw.pivot_table(index='date',columns=['type','zero'],values='g',aggfunc='sum').fillna(0)
ex0=(p[('call',False)]+p[('put',False)])/1e9
c=sqlite3.connect(f"file:{B}.cache/gex_database.db?mode=ro",uri=True)
db=pd.read_sql("select date,total_gex,options_count from daily_gex_metrics where symbol='SPY' and date like '2024%'",c).set_index('date')
ph=set(db.index[db.options_count.isna()])
y=yaml.load(open(B+'reports/validation/paper2_regime_windows/phase3_baseline_2024_full_year.yaml'),Loader=yaml.CSafeLoader)
yl={w['window_id']:(w['regime_detected'],w['regime_type']) for w in y['windows']}
rows=[json.loads(l) for l in open(B+'reports/validation/paper2_regime_windows/batch_jobs/phase3_full_2024_baseline_v2.jsonl')]
def rule(v,thr=21):
    v=np.array(v); n=max((v>0).sum(),(v<0).sum()); f=int((np.sign(v[1:])!=np.sign(v[:-1])).sum())
    return n>=thr and np.abs(v).mean()>=5 and f<=5, f
res=[];mm=0;mm22=0;mmrep=0
for r in rows:
    s=re.findall(r'(\d{4}-\d{2}-\d{2}): ([+-][\d.]+)B',r['body']['messages'][0]['content'])
    d=[a for a,b in s]; v=[float(b) for a,b in s]
    cid=r['custom_id']; lab=yl[cid][0] if cid in yl else None
    if cid not in yl: print('missing',cid)
    det,f=rule(v); det22,_=rule(v,22)
    v2=[-ex0[a] if a in ph else x for a,x in zip(d,v)]; detr,_=rule(v2)
    mm+= det!=lab; mm22+=det22!=lab; mmrep+= (not detr)
    res.append(dict(id=cid,lab=lab,rule=det,flips=f,nph=sum(a in ph for a in d),nph_feb_mar=sum(a in ph and a<'2024-04' for a in d),rtype=yl[cid][1]))
o=pd.DataFrame(res)
print('rule vs yaml mismatches (>=21):',mm,' (>=22):',mm22,' replaced-not-detected:',mmrep)
print(o.groupby('lab').size())
rej=o[~o.lab.astype(bool)]
print('rejected',len(rej),rej.rtype.value_counts().to_dict()); print('nph dist rejected',rej.nph.value_counts().sort_index().to_dict(),'flips range',rej.flips.min(),rej.flips.max())
print('feb-mar ph in rejected min',rej.nph_feb_mar.min(), 'june ph in rejected',(rej.nph-rej.nph_feb_mar).sum())
det=o[o.lab.astype(bool)]; print('detected nph dist',det.nph.value_counts().sort_index().to_dict(),'flips range',det.flips.min(),det.flips.max())
print('rejected end dates',rej.id.min(),rej.id.max())
# persistence stats yaml
