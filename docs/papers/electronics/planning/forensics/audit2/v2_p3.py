import json,re,sqlite3,yaml,numpy as np,pandas as pd
B='/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns/'
raw=pd.read_csv('v2_raw_2024.csv'); 
p=raw.pivot_table(index='date',columns=['type','zero'],values='g',aggfunc='sum').fillna(0)
p.columns=[f'{a}_{"z" if b else "x"}' for a,b in p.columns]
p['ex0']=p.call_x+p.put_x; p['all']=p.ex0+p.call_z+p.put_z; p['signed_all']=p.call_x+p.call_z-p.put_x-p.put_z
c=sqlite3.connect(f"file:{B}.cache/gex_database.db?mode=ro",uri=True)
db=pd.read_sql("select date,total_gex,net_call_gex,net_put_gex,options_count,spot_price,created_at from daily_gex_metrics where symbol='SPY' and date like '2024%'",c).set_index('date')
db['t']=db.total_gex/1e9
j=db.join(p/1e9)
real=j[j.options_count.notna()]
print('real',len(real),'placeholder',len(j)-len(real))
print('db neg',(db.total_gex<0).sum(),'pos',(db.total_gex>0).sum())
re_=(real.t+real.ex0).abs()/real.ex0
print('rel err vs -(ex0): med %.4f p90 %.4f within5%% %d'%(re_.median(),re_.quantile(.9),(re_<.05).sum()), 'corr',np.corrcoef(real.t,-real.ex0)[0,1])
re2=(real.t+real['all']).abs()/real['all']; print('vs -(all): med %.4f within5%% %d'%(re2.median(),(re2<.05).sum()))
print(j.loc[['2024-01-02','2024-03-15'],['t','call_x','put_x','call_z','put_z','ex0']])
# placeholder
print(j[j.options_count.isna()][['t','spot_price','ex0','created_at']])
# prompt series
rows=[json.loads(l) for l in open(B+'reports/validation/paper2_regime_windows/batch_jobs/phase3_full_2024_baseline_v2.jsonl')]
y=yaml.load(open(B+'reports/validation/paper2_regime_windows/phase3_baseline_2024_full_year.yaml'),Loader=yaml.CSafeLoader)
lab={w.get('window_id') or w.get('custom_id') or w.get('end_date'):w for w in y['windows']}
print(list(y['windows'][0].keys())[:15])
ph=set(j.index[j.options_count.isna()])
allv=0;neg=0;mism=0
out=[]
for r in rows:
    t=r['body']['messages'][0]['content']
    s=re.findall(r'(\d{4}-\d{2}-\d{2}): ([+-][\d.]+)B',t)
    assert len(s)==30
    for d,v in s:
        allv+=1;neg+=float(v)<0
        if abs(float(v)-db.t[d])>0.006: mism+=1
    vals=np.array([float(v) for d,v in s]); dts=[d for d,v in s]
    npos=(vals>0).sum();nneg=(vals<0).sum()
    flips=int((np.sign(vals[1:])!=np.sign(vals[:-1])).sum())
    det=(max(npos,nneg)>=21) and np.abs(vals).mean()>=5 and flips<=5
    out.append((r['custom_id'],det,sum(d in ph for d in dts),flips))
print('values',allv,'neg',neg,'mismatch vs db',mism)
o=pd.DataFrame(out,columns=['id','rule','nph','flips'])
yl={}
for w in y['windows']:
    yl[w['window_id'] if 'window_id' in w else None]=w['regime_detected']
print(o.shape)
