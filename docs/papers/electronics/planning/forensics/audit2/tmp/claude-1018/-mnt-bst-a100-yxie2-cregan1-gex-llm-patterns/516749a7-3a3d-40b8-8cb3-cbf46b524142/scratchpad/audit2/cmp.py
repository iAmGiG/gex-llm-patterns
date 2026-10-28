import sqlite3, pandas as pd, numpy as np
pg=pd.read_csv("/tmp/claude-1018/-mnt-bst-a100-yxie2-cregan1-gex-llm-patterns/516749a7-3a3d-40b8-8cb3-cbf46b524142/scratchpad/audit2/pg_summary.csv",header=None,names=["date","spot","tot","call","put","reg"])
con=sqlite3.connect("file:.cache/gex_database.db?mode=ro",uri=True)
db=pd.read_sql("select date,spot_price s,total_gex t,net_call_gex c,net_put_gex p from daily_gex_metrics where symbol='SPY' and date like '2024%'",con)
m=db.merge(pg,on="date",how="left")
m["ph"]=(m.c==0)&(m.p==0)
r=m[~m.ph]
print("pg 2024 rows",len(pg[pg.date.str.startswith('2024')]),"matched",m.tot.notna().sum())
print("pg signed tot 2024: neg days",(m.tot<0).sum(),"pos",(m.tot>0).sum(),"of",m.tot.notna().sum())
for name,x in [("pg tot",m.tot),("-pg tot",-m.tot),("pg call",m.call),("-pg(call-put)",-(m.call-m.put)), ("-(call+|put|)",-(m.call+m.put.abs()))]:
    print(name,"corr real",np.corrcoef(r.t,x[~m.ph])[0,1],"median ratio",np.median(r.t/x[~m.ph]))
print("sign agreement db vs pg tot real:",(np.sign(r.t)==np.sign(r.tot)).mean(), "pg tot negative on real days:",(r.tot<0).sum())
print("db t/ (pg call+pg put) ...")
print("c,p db vs pg call/put: ratios",np.median(r.c/r.call),np.median(r.p/r.put))
print("db c vs -pg call corr",np.corrcoef(r.c,-r.call)[0,1],"db p vs pg put",np.corrcoef(r.p,r.put)[0,1], "db p vs -pg put",np.corrcoef(r.p,-r.put)[0,1])
print(m[["date","s","spot","t","tot","call","put"]].head(5).to_string())
# spot vs SPY
m["gap"]=(m.s/m.spot-1)*100
print("placeholder spot gap %:"); print(m[m.ph][["date","s","spot","gap"]].to_string())
print("real spot gap %: min/max",r.assign(g=(r.s/r.spot-1)*100).g.agg(['min','max']).tolist())
print("pg tot mean/neg frac on 242:", r.tot.mean()/1e9)
m.to_csv("/tmp/claude-1018/-mnt-bst-a100-yxie2-cregan1-gex-llm-patterns/516749a7-3a3d-40b8-8cb3-cbf46b524142/scratchpad/audit2/cmp2024.csv",index=False)
