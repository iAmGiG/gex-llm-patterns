import sqlite3, pandas as pd, numpy as np
con=sqlite3.connect("file:.cache/consolidated_historical.db?mode=ro",uri=True)
df=pd.read_sql("select date,option_type t,expiration e,open_interest oi,gamma g,underlying_price s from raw_options_chain where symbol='SPY' and date like '2024%'",con)
print(len(df), df.s.isna().sum(), df.g.isna().sum())
df['spot']=df.groupby('date').s.transform('max')  # as per extractor
df['gx']=df.g*df.oi*100*df.spot**2*0.01
df['ex0']=df.e>df.date
def agg(d):
    c=d[d.t=='call'].gx.sum(); p=d[d.t=='put'].gx.sum()
    c0=d[(d.t=='call')&d.ex0].gx.sum(); p0=d[(d.t=='put')&d.ex0].gx.sum()
    return pd.Series(dict(call_all=c,put_all=p,call_ex0=c0,put_ex0=p0,signed_all=c-p,signed_ex0=c0-p0,gross_ex0=-(c0+p0),gross_all=-(c+p)))
r=df.groupby('date').apply(agg)/1e9
r.to_csv('/tmp/claude-1018/-mnt-bst-a100-yxie2-cregan1-gex-llm-patterns/516749a7-3a3d-40b8-8cb3-cbf46b524142/scratchpad/audit2/p1_raw_recompute.csv')
u=pd.read_csv('reports/statistical_validation/gamma_positioning_timeseries_2024.csv').set_index('date')
r['csv']=u.net_gex/1e9
db=sqlite3.connect("file:.cache/consolidated_historical.db?mode=ro",uri=True)
s=pd.read_sql("select date,total_gex/1e9 stored from daily_gex_metrics where symbol='SPY'",db).set_index('date'); r['stored']=s.stored
g=sqlite3.connect("file:.cache/gex_database.db?mode=ro",uri=True)
s2=pd.read_sql("select date,total_gex/1e9 gdb from daily_gex_metrics where symbol='SPY'",g).set_index('date'); r['gdb']=s2.gdb
pd.set_option('display.width',250)
print(r.round(2).loc[['2024-01-02','2024-01-09','2024-01-17','2024-01-18','2024-01-19','2024-03-05','2024-03-06','2024-03-13','2024-03-15','2024-06-05','2024-06-07','2024-06-21','2024-06-28']])
m=r.dropna(subset=['csv'])
print(len(m))
for c in ['gross_ex0','gross_all','signed_all','signed_ex0']:
    print(c,'corr',m[c].corr(m.csv).round(4),'med abs rel err',((m[c]-m.csv).abs()/m.csv.abs()).median().round(4), 'neg days',(r[c]<0).sum(),'/',len(r),'mean',r[c].mean().round(2))
print('signed_all on 72: neg',(r.signed_all<0).sum(),'< -2:',(r.signed_all<-2).sum(),'mean',r.signed_all.mean())
d13=r.loc[['2024-01-02','2024-01-09','2024-01-17','2024-01-18','2024-01-19','2024-03-05','2024-03-06','2024-03-13','2024-03-15','2024-06-05','2024-06-07','2024-06-21','2024-06-28']]
for c in ['signed_all','signed_ex0']:
    print(c,'13dates neg',(d13[c]<0).sum(),'< -2',(d13[c]<-2).sum(),d13[c].min().round(2),d13[c].max().round(2))
