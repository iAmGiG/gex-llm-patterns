import psycopg2, pandas as pd, sys
y=sys.argv[1]
cn=psycopg2.connect(host="127.0.0.1",user="cregan1",dbname="gex_options"); cur=cn.cursor()
cur.execute("SET statement_timeout='600s'"); cur.execute("SET enable_seqscan=off")
cur.execute("""select trading_date, option_type, (expiration=trading_date) z, sum(gamma*open_interest*100.0*underlying_price*underlying_price*0.01)/1e9, count(*)
from gex.options_chains_partitioned where symbol='SPY' and trading_date between %s and %s group by 1,2,3""",(y+'-01-01',y+'-12-31'))
pd.DataFrame(cur.fetchall(),columns=['date','typ','z','gex','n']).to_csv(f"{sys.argv[2]}/raw_{y}.csv",index=False)
