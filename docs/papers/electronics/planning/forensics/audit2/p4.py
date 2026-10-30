import json,re,sqlite3,pandas as pd,numpy as np,os,glob
vals={}
for l in open("reports/validation/paper2_regime_windows/batch_jobs/batch_regime_20251120_104630.jsonl"):
    c=json.loads(l)['body']['messages'][0]['content']
    for dt,x in re.findall(r'^(\d{4}-\d{2}-\d{2}): ([+-]?[\d.]+)B',c,re.M): vals[dt]=float(x)
s=pd.Series(vals).sort_index(); print("phase4 series n",len(s),"pos",(s>0).sum(),"zero",(s==0).sum(),"neg",(s<0).sum(),"mean",s.mean())
con=sqlite3.connect("file:.cache/consolidated_historical.db?mode=ro",uri=True)
c=pd.read_sql("select * from daily_gex_metrics where symbol='SPY' and date like '2020%'",con).set_index('date')
print(len(c), c.columns.tolist())
m=pd.DataFrame({'p4':s}).join(c[['total_gex','net_call_gex','net_put_gex','gex_oi','gex_volume','spot_price']]/1)
for col in ['total_gex','net_call_gex','net_put_gex','gex_oi','gex_volume']:
    x=m[col]/1e9 if m[col].abs().max()>1e6 else m[col]
    print(col,"scale max",m[col].abs().max(),"corr raw",np.corrcoef(m.p4,x)[0,1],"corr |x|",np.corrcoef(m.p4,x.abs())[0,1])
print("gex_oi neg days",(m.gex_oi<0).sum(),"total_gex neg",(m.total_gex<0).sum())
r=(m.p4/(m.gex_oi.abs()/ (1e9 if m.gex_oi.abs().max()>1e6 else 1)))
print("p4/|gex_oi| ratio: min/med/max",r.min(),r.median(),r.max())
# today's pg
pg=pd.read_csv(f"{os.path.dirname('x')}/tmp/claude-1018/-mnt-bst-a100-yxie2-cregan1-gex-llm-patterns/516749a7-3a3d-40b8-8cb3-cbf46b524142/scratchpad/audit2/pg_summary.csv".replace("/tmp/claude","/tmp/claude") ,header=None,names=["date","spot","tot","call","put","reg"]).set_index('date')
m=m.join(pg[['tot','call','put']])
print("PG 2020 signed tot: neg days",(m.tot<0).sum(),"of",m.tot.notna().sum())
print("corr p4 vs pg tot",np.corrcoef(m.p4,m.tot/1e9)[0,1],"vs |pg tot|",np.corrcoef(m.p4,m.tot.abs()/1e9)[0,1])
print("corr p4 vs pg tot, on neg days:",m[m.tot<0].p4.describe().to_dict())
m.to_csv("/tmp/claude-1018/-mnt-bst-a100-yxie2-cregan1-gex-llm-patterns/516749a7-3a3d-40b8-8cb3-cbf46b524142/scratchpad/audit2/cmp2020.csv")
print(m.head(8).to_string())
