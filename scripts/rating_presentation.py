"""Bộ lọc chung cho tab và báo cáo tín nhiệm ở mọi ngành."""
MARKET_METRICS = frozenset({'Price','PE','PB','EV_EBITDA','FairValue'})
MARKET_LABELS = frozenset({'Giá thị trường','P/E','P/B','EV/EBITDA'})

def credit_metrics(metrics):
    return [m for m in metrics if m not in MARKET_METRICS]

def credit_header(items):
    return [(label,value) for label,value in items if label not in MARKET_LABELS]

def credit_pack(pack):
    result=dict(pack)
    result['Items']={m:x for m,x in pack['Items'].items() if m not in MARKET_METRICS}
    result['Sections']=[(g,credit_metrics(ms)) for g,ms in pack['Sections'] if credit_metrics(ms)]
    return result
