import json,re,sqlite3,math,collections
B="reports/validation/paper2_regime_windows/batch_jobs/"
inp={}
for l in open(B+"phase4a_postgresql_20260104_184832.jsonl"):
    d=json.loads(l); t=d["body"]["messages"][0]["content"]
    v=re.findall(r"Day T([-+]\d+): ([+-][\d.]+)B",t)
    assert len(v)==30,(d["custom_id"],len(v))
    inp[d["custom_id"]]=[float(x[1]) for x in v]
print("input windows",len(inp))
out={}; bad=[]
for l in open(B+"results_phase4a_postgresql_20260104_193513.jsonl"):
    d=json.loads(l); cid=d["custom_id"]
    try:
        c=d["response"]["body"]["choices"][0]["message"]["content"]
        j=json.loads(c); out[cid]=j
    except Exception as e: bad.append(cid)
print("output parsed",len(out),"bad",len(bad))
def rule(v):
    pos=sum(x>0 for x in v); neg=sum(x<0 for x in v)
    pers=max(pos,neg); mag=sum(abs(x) for x in v)/30
    fl=sum(1 for a,b in zip(v,v[1:]) if (a>0)!=(b>0) and a!=0 and b!=0)
    return pers>=21 and mag>=5 and fl<=5, pers,mag,fl
# output file
mis=[];n=0
for k,j in out.items():
    r=rule(inp[k])
    n+=1
    if bool(j["regime_detected"])!=r[0]: mis.append((k,j["regime_detected"],r,j.get("persistence_pct"),j.get("avg_magnitude_billions"),j.get("sign_flips")))
print("output vs rule: n",n,"mismatches",len(mis))
for m in mis[:20]: print(m)
# cache
c=sqlite3.connect("file:.cache/research_cache.db?mode=ro",uri=True)
rows=c.execute("select trading_date,detected,structured_output from llm_detections where pattern_id='regime_30day'").fetchall()
print("cache rows",len(rows), "detected",sum(r[1] for r in rows))
mis2=[];missing=[]
for td,det,so in rows:
    k="window-"+td
    if k not in inp: missing.append(td); continue
    r=rule(inp[k])
    if bool(det)!=r[0]: mis2.append((td,det,r))
print("cache vs rule mismatches",len(mis2),"missing inputs",len(missing)); print(mis2[:10])
# year stats
yr=collections.defaultdict(lambda:[0,0,[],[]])
tot=0
for td,det,so in rows:
    y=td[:4]; k="window-"+td
    yr[y][0]+=1; yr[y][1]+=det
    yr[y][2].append(sum(abs(x) for x in inp[k])/30)
    j=json.loads(so); yr[y][3].append(j.get("avg_magnitude_billions"))
for y in sorted(yr):
    n,d,m,lm=yr[y]; lm=[x for x in lm if x is not None]
    print(y,n,d,round(100*d/n,1),"inputmean",round(sum(m)/n,2),"LLMmean",round(sum(lm)/len(lm),2))
N=len(rows);D=sum(r[1] for r in rows)
def wilson(k,n,z=1.96):
    p=k/n;den=1+z*z/n;ctr=(p+z*z/(2*n))/den;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return round(100*(ctr-h),1),round(100*(ctr+h),1)
print("total",D,N,D/N,wilson(D,N))
# break
pre=[r for r in rows if r[0]<"2023-09-29"];post=[r for r in rows if r[0]>="2023-09-29"]
print("pre",len(pre),sum(r[1] for r in pre),"post",len(post),sum(r[1] for r in post))
print("2024-25 detections",sum(r[1] for r in rows if r[0]>="2024"))
# 2020/2021 mean growth
import statistics
for a,b in [("2020","2024"),("2021","2024"),("2021","2025"),("2020","2025")]:
    ma=sum(yr[a][2])/len(yr[a][2]);mb=sum(yr[b][2])/len(yr[b][2]);print(a,b,round(ma,2),round(mb,2),"growth%",round(100*(mb/ma-1),1))
# pooled day-level mean
