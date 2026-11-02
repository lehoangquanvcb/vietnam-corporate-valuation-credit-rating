"""Hồi quy CAR trống, trục năm và khoảng trống dữ liệu trên giao diện."""
import pandas as pd
import plotly.graph_objects as go
from scripts.financial_charts import history_figure, peer_figure, clean_figure


def test_missing_history_has_no_chart_but_real_zero_remains():
    h=pd.DataFrame({'DisplayPeriod':['2021','2022','2023','2024','2025'],
                    'Value':[None]*5,'PeerMean':[None]*5,'Status':['MISSING']*5})
    assert history_figure(h,'OWN','History') is None
    h.loc[2,['Value','Status']]=[0.,'OK']
    fig=history_figure(h,'OWN','History')
    assert len(fig.data)==1
    assert list(fig.data[0].y)==[None,None,0.,None,None]
    assert not fig.data[0].connectgaps
    assert list(fig.layout.xaxis.tickvals)==h.DisplayPeriod.tolist()
    assert fig.layout.xaxis.type=='category'


def test_invalid_values_do_not_produce_blank_or_infinite_traces():
    h=pd.DataFrame({'DisplayPeriod':['2023','2024','2025'],'Value':[1,float('inf'),3],
                    'Status':['ERROR','OK','OK'],'PeerMean':[2,None,4]})
    fig=history_figure(h,'OWN','History',100,'%')
    assert list(fig.data[0].y)==[None,None,300.]
    assert list(fig.data[1].y)==[200.,None,400.]
    assert peer_figure(pd.DataFrame({'Ticker':['OWN'],'Value':[float('inf')]}),'OWN','Peer') is None


def test_peer_mean_excludes_issuer_and_requires_five_peers():
    q=pd.DataFrame({'Ticker':['OWN','A','B','C','D','E'],'Value':[1000,1,2,3,4,5]})
    fig=peer_figure(q,'OWN','Peer')
    assert fig.layout.shapes[0].y0==3
    assert not peer_figure(q.iloc[:-1],'OWN','Peer').layout.shapes


def test_insurance_missing_first_segment_keeps_legend_and_missing_year():
    f=go.Figure()
    f.add_scatter(x=['2021'],y=[None],legendgroup='company',showlegend=True)
    f.add_scatter(x=['2023'],y=[4],legendgroup='company',showlegend=False)
    result=clean_figure(f,['2021','2022','2023'])
    assert len(result.data)==1 and result.data[0].showlegend
    assert list(result.layout.xaxis.categoryarray)==['2021','2022','2023']


def test_sparse_car_is_not_carried_into_year_end_or_current_quarter(tmp_path):
    from scripts.financial_evidence import same_period_history,repair_snapshot,at_period
    (tmp_path/'data/raw').mkdir(parents=True)
    pd.DataFrame([dict(Ticker='ABB',Metric='TotalAssets',Value=100,Period='2026-Q2'),
                  dict(Ticker='ABB',Metric='CAR',Value=.0987,Period='2025-Q2')]).to_csv(tmp_path/'data/bank_history_long.csv',index=False)
    h=same_period_history('ABB','BANK','FY',5,tmp_path,['CAR'])
    assert repair_snapshot('ABB','BANK',root=tmp_path)['CAR_AsOf']=='2025-Q2'
    assert h.Value.isna().all()
    assert history_figure(h,'ABB','CAR') is None
    assert at_period('ABB','BANK','2026-Q2','QUARTER',tmp_path)['CAR']['Value'] is None


def test_insurance_year_axis_and_missing_figures():
    from scripts.insurance_analysis import metric_pair,figures
    pair=metric_pair('ABI','Equity')
    h,q=figures(pair)
    assert h.layout.xaxis.type=='category'
    assert list(h.layout.xaxis.tickvals)==pair['History'].DisplayPeriod.tolist()
    from copy import deepcopy
    missing=deepcopy(pair)
    for key in ['History','Peers']:
        missing[key]['Value']=None
        missing[key]['Status']='MISSING'
    missing['PeerHistory']['PeerMean']=None
    h,q=figures(missing)
    assert h is None and q is None
