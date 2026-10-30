import json,re,sqlite3,numpy as np,pandas as pd
from statsmodels.stats.proportion import proportion_confint
B='/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns/'
inp={}
for l in open(B+'reports/validation/paper2_regime_windows/batch_jobs/phase4a_postgresql_20260104_184832.jsonl'):
    r=json.loads(l); t=r['body']['messages'][0]['content']
    s=re.findall(r'Day T([-+]\d+): ([+-][\d.]+)B',t); inp[r['custom_id']]=[float(v) for k,v in s]
print(len(inp),set(len(v) for v in inp.values()),list(inp)[:2])
c=sqlite3.connect(f"file:{B}.cache/research_cache.db?mode=ro",uri=True)
print(c.execute("select sql from sqlite_master where name='llm_detections'").fetchone()[0][:600])
df=pd.read_sql("select * from llm_detections where pattern_id='regime_30day'",c)
print(len(df),df.columns.tolist())
def rule(v):
    v=np.array(v); n=max((v>0).sum(),(v<0).sum()); f=int((np.sign(v[1:])!=np.sign(v[:-1])).sum())
    return bool(n>=21 and np.abs(v).mean()>=5 and f<=5)
df['cid']=df.trading_date.map(lambda d:'window-'+d[:10])
print(df.cid.isin(inp).sum())
df['rule']=df.cid.map(lambda k:rule(inp[k])); df['mabs']=df.cid.map(lambda k:np.abs(inp[k]).mean()); df['neg']=df.cid.map(lambda k:sum(x<0 for x in inp[k]))
print('mismatch',(df.rule!=df.detected.astype(bool)).sum())
df['yr']=df.trading_date.str[:4]
g=df.groupby('yr').agg(n=('detected','size'),det=('detected','sum'),mabs=('mabs','mean'),negdays=('neg','sum'),med=('mabs','median'))
g['rate']=g.det/g.n*100; print(g)
print('pooled 24-25 mean',df[df.yr>='2024'].mabs.mean(), 'share windows >=23',(df[df.yr>='2024'].mabs>=23).sum(),'of',(df.yr>='2024').sum())
llm=df.structured_output.map(lambda s:json.loads(s).get('avg_magnitude_billions')); df['llm']=pd.to_numeric(llm); print(df.groupby('yr').llm.mean().round(2).to_dict())
for a,b in [(2.97,20.35),(4.88,20.35),(4.88,18.97),(2.97,18.97),(5,23)]: print(a,b,'%.1f%%'%((b/a-1)*100))
print('rounded',(20.3/3.0-1)*100)
tot=df.detected.sum(); print(tot,len(df),proportion_confint(tot,len(df),method='wilson'))
pre=df[df.trading_date<'2023-09-29']; post=df[df.trading_date>='2023-09-29']
print('pre',len(pre),pre.detected.sum(),pre.detected.mean(),'post',len(post),post.detected.sum(),post.detected.mean(), post.detected.sum()/tot)
print('2024-25 det',df[df.yr>='2024'].detected.sum(), df[df.yr>='2024'].detected.sum()/tot)
# windows fully after break: all positive series? check any negative day in post windows
print('neg days in windows ending >=2023-09-29',post.neg.sum(), 'pre windows neg days',pre.neg.sum(), 'pre windows with any neg',(pre.neg>0).sum())
# first window end with 0 neg days and fully call-only
