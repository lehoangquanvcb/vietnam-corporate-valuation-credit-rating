"""Bình quân peer lịch sử: tính riêng từng kỳ, không lấy số quý hiện tại lấp về quá khứ."""
import pandas as pd
from scripts.insurance_peers import period_peers, included_rows
from scripts.universal_data import universe

ENGINE_VERSION = '8.125.0'
HISTORY_PEER_NOTE = ('Bình quân số học của các peer có số hợp lệ cùng kỳ và cùng cơ sở, '
                     'không gồm doanh nghiệp đang phân tích; không gia quyền. '
                     'N là số peer thực dùng từng mốc. Mẫu ít doanh nghiệp chỉ có ý nghĩa đối chiếu. '
                     'Đường được ngắt khi thiếu số, thay đổi thành phần mẫu hoặc có đứt gãy nguồn.')


def historical_peer_benchmark(ticker,metric,history,basis,peers):
    companies={r['Ticker']:r for r in universe().to_dict('records')}
    rows=[];evidence=[];breaks=[];previous=None
    for i,h in enumerate(history.itertuples()):
        frame=period_peers(ticker,metric,h.Period,peers,basis,companies)
        z=included_rows(frame.iloc[1:]);members=tuple(sorted(z.Ticker))
        rows.append(dict(Period=h.Period,DisplayPeriod=h.DisplayPeriod,
                         PeerMean=float(z.Value.mean()) if len(z) else float('nan'),
                         PeerCount=len(z),PeerTickers=members,Basis=h.Basis))
        current={r.Ticker:r for r in z.itertuples()}
        if previous is not None:
            changed=set(previous)!=set(current)
            for t in set(previous)&set(current):
                a,b=previous[t],current[t]
                if a.Basis!=b.Basis:changed=True
                if metric in ('InsuranceReserves','InsuranceReservesEquity','ReservesPremium'):
                    if a.Value>0 and b.Value>0 and max(a.Value,b.Value)/min(a.Value,b.Value)>100:changed=True
            if changed:breaks.append(i)
        previous=current
        frame=frame.copy();frame['DisplayPeriod']=h.DisplayPeriod;evidence.append(frame)
    return dict(PeerHistory=pd.DataFrame(rows,columns=['Period','DisplayPeriod','PeerMean','PeerCount','PeerTickers','Basis']),
                PeerHistoryEvidence=pd.concat(evidence,ignore_index=True) if evidence else pd.DataFrame(),
                PeerHistoryBreaks=breaks,PeerHistoryNote=HISTORY_PEER_NOTE)


def history_peer_sentence(pair):
    """Vị trí và khoảng cách nhiều năm, chỉ so xu hướng khi thành phần mẫu nhất quán."""
    from scripts.insurance_presentation import format_metric as fmt
    from scripts.methodology_kpi_engine import PCT,MULT
    from scripts.insurance_narrative import number,decimal
    h=pair.get('History',pd.DataFrame());p=pair.get('PeerHistory',pd.DataFrame());m=pair['Metric']
    if h.empty or p.empty:return ''
    matches=[]
    for a,b in zip(h.itertuples(),p.itertuples()):
        if a.Status=='OK' and number(a.Value) is not None and number(b.PeerMean) is not None:
            matches.append((a,b))
    if not matches:return 'Chưa có mốc lịch sử đủ số của cả doanh nghiệp và peer để đối chiếu.'
    a,b=matches[-1];relation='cao hơn' if a.Value>b.PeerMean else 'thấp hơn' if a.Value<b.PeerMean else 'bằng'
    text=f'Tại {a.DisplayPeriod}, doanh nghiệp {relation} bình quân {b.PeerCount} peer là {fmt(m,b.PeerMean,"OK")}.'
    if len(matches)>1:
        x,y=matches[0]
        if pair.get('HistoryBreaks') or pair.get('PeerHistoryBreaks'):
            text+=' Không suy ra xu hướng khoảng cách xuyên qua mốc thay đổi mẫu hoặc đứt gãy nguồn.'
        elif m in PCT or m in MULT:
            scale=100 if m in PCT else 1;unit='điểm phần trăm' if m in PCT else 'lần'
            first=(x.Value-y.PeerMean)*scale;last=(a.Value-b.PeerMean)*scale
            text+=f' Chênh lệch doanh nghiệp trừ bình quân peer từ {decimal(first)} {unit} tại {x.DisplayPeriod} thành {decimal(last)} {unit} tại {a.DisplayPeriod}.'
        elif x.Value>0 and a.Value>0 and y.PeerMean>0 and b.PeerMean>0:
            text+=f' Quy mô tương đối từ {decimal(x.Value/y.PeerMean)} lần bình quân tại {x.DisplayPeriod} thành {decimal(a.Value/b.PeerMean)} lần tại {a.DisplayPeriod}.'
    return text
