import psycopg2,pandas as pd,sys
yr=int(sys.argv[1])
c=psycopg2.connect(host='127.0.0.1',user='cregan1',dbname='gex_options')
cur=c.cursor(); cur.execute("SET statement_timeout='600s'"); cur.execute("SET enable_seqscan=off")
cur.execute("""select trading_date, option_type, (expiration=trading_date) as z,
 sum(gamma*open_interest*100*underlying_price*underlying_price*0.01) g, count(*)
 from gex.options_chains_partitioned where symbol='SPY' and trading_date>=%s and trading_date<%s
 and gamma is not null and open_interest is not null group by 1,2,3""",(f'{yr}-01-01',f'{yr+1}-01-01'))
df=pd.DataFrame(cur.fetchall(),columns=['date','type','zero','g','n']); df.to_csv(f'v2_raw_{yr}.csv',index=False); print(df.shape, df.option_type.unique() if 'option_type' in df else df.type.unique())
