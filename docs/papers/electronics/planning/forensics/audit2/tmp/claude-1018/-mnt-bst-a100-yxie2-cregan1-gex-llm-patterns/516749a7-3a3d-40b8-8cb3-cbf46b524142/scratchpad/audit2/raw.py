import psycopg2, sqlite3, pandas as pd, numpy as np, sys
cn=psycopg2.connect(host="127.0.0.1",user="cregan1",dbname="gex_options"); cur=cn.cursor()
cur.execute("SET statement_timeout='600s'")
con=sqlite3.connect("file:.cache/gex_database.db?mode=ro",uri=True)
dates=['2024-01-02','2024-03-15','2024-05-24','2024-09-10','2024-12-18','2024-02-02','2024-06-04']
out=[]
for d in dates:
    cur.execute("""select option_type, (expiration=trading_date) z, sum(gamma*open_interest*100.0*underlying_price*underlying_price*0.01)/1e9, count(*)
    from gex.options_chains_partitioned where symbol='SPY' and trading_date=%s group by 1,2""",(d,))
    rows=cur.fetchall()
    r=con.execute("select total_gex/1e9,net_call_gex/1e9,net_put_gex/1e9,options_count from daily_gex_metrics where symbol='SPY' and date=?",(d,)).fetchone()
    print(d,"raw(type,is0dte,gex$B,n):",[(a,b,round(c,2),n) for a,b,c,n in rows],"| DB tot,c,p,n:",[round(x,2) if x is not None else None for x in r])
