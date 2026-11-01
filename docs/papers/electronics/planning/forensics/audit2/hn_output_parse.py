import json,re,sqlite3,collections
B="reports/validation/paper2_regime_windows/batch_jobs/"
inp={}
for l in open(B+"phase4a_postgresql_20260104_184832.jsonl"):
    d=json.loads(l); t=d["body"]["messages"][0]["content"]
    inp[d["custom_id"]]=[float(x[1]) for x in re.findall(r"Day T([-+]\d+): ([+-][\d.]+)B",t)]
def rule(v):
    pos=sum(x>0 for x in v); neg=sum(x<0 for x in v)
    fl=sum(1 for a,b in zip(v,v[1:]) if (a>0)!=(b>0))
    return max(pos,neg)>=21 and sum(abs(x) for x in v)/30>=5 and fl<=5
res={};unp=[];st=collections.Counter()
for l in open(B+"results_phase4a_postgresql_20260104_193513.jsonl"):
    d=json.loads(l);cid=d["custom_id"];st[d["response"]["status_code"]]+=1
    t=d["response"]["body"]["choices"][0]["message"]["content"]
    m=re.search(r'"regime_detected"\s*:\s*(true|false)',t)
    if not m: unp.append(cid);continue
    res[cid]=m.group(1)=="true"
print("status",st,"parsed(regex)",len(res),"unparsed",len(unp))
mis=[k for k,v in res.items() if v!=rule(inp[k])]
print("mismatch vs rule",len(mis),mis[:10])
print("detected in parsed",sum(res.values()))
c=sqlite3.connect("file:.cache/research_cache.db?mode=ro",uri=True)
cache={ "window-"+r[0]:r[1] for r in c.execute("select trading_date,detected from llm_detections where pattern_id='regime_30day'")}
print("regex-parsed not in cache",len(set(res)-set(cache)),"cache not in regex-parsed",len(set(cache)-set(res)))
print("cache vs regex-parsed disagreement",sum(1 for k in cache if k in res and bool(cache[k])!=res[k]))
# rule on all 1476 inputs, and on those unparsed
print("rule detected over all 1476",sum(rule(v) for v in inp.values()))
# threshold edge: ties
edge=[k for k,v in inp.items() if abs(sum(abs(x) for x in v)/30-5)<0.02 or max(sum(x>0 for x in v),sum(x<0 for x in v))==20]
print("edge cases",len(edge))
# flips definition note: zeros
print("windows with zero value",sum(1 for v in inp.values() if 0.0 in v))
