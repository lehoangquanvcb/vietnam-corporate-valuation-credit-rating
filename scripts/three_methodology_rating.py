import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
import numpy as np
import pandas as pd
from scripts.universal_data import get_company,get_snapshot,num

ROOT=Path(__file__).resolve().parents[1]
SCALE=['aaa','aa+','aa','aa-','a+','a','a-','bbb+','bbb','bbb-','bb+','bb','bb-','b+','b','b-','ccc','cc','c']
VN={x:'vn'+x.upper() for x in SCALE}
NOTCH={'Rất Mạnh':2,'Mạnh':1,'Phù Hợp':0,'Trung Bình':-1,'Yếu':-2,'Rất Yếu':-4}

def move(rating,n):
    r=str(rating).lower().replace('vn','')
    if r not in SCALE:return rating
    return SCALE[max(0,min(len(SCALE)-1,SCALE.index(r)-int(n)))]

def label(x):
    x=str(x).lower().replace('vn','')
    return VN.get(x,'vn'+x.upper())

def _relative(v,bench,lower=False):
    v=num(v);b=num(bench)
    if v is None or b in (None,0):return 'Phù Hợp'
    gap=v/b-1
    if lower:gap=-gap
    if gap>=.30:return 'Rất Mạnh'
    if gap>=.10:return 'Mạnh'
    if gap<=-.35:return 'Yếu'
    if gap<=-.15:return 'Trung Bình'
    return 'Phù Hợp'

def _industry_mean(ticker,metric):
    try:
        from scripts.sector_benchmark_engine import industry_snapshot
        z=industry_snapshot(ticker)
        if len(z) and metric in z:
            v=pd.to_numeric(z[metric],errors='coerce').dropna()
            return float(v.mean()) if len(v) else None
    except Exception:pass
    return None

def bank_rating(ticker, overrides=None):
    s=get_snapshot(ticker); o=overrides or {}
    anchor='a-'
    bp=o.get('BusinessProfile','Phù Hợp')
    ce=o.get('CapitalEarnings',_relative(s.get('ROE'),_industry_mean(ticker,'ROE')))
    rp=o.get('RiskPosition',_relative(s.get('NPL'),_industry_mean(ticker,'NPL'),lower=True))
    fl=o.get('FundingLiquidity',_relative(s.get('CASA'),_industry_mean(ticker,'CASA')))
    factors={'Hồ sơ Kinh doanh':bp,'Vốn và Lợi nhuận':ce,'Vị thế Rủi ro':rp,'Huy động vốn và Thanh khoản':fl}
    notches=sum(NOTCH.get(v,0) for v in factors.values())
    sacp=move(anchor,notches)
    support=int(o.get('ExternalSupportNotches',0));icr=move(sacp,support)
    return {'Methodology':'BANK','MethodologyName':'Phương pháp XHTN Ngân hàng','BICRA':'a-','Anchor':label(anchor),'Factors':factors,'InternalNotches':notches,'SACP':label(sacp),'ExternalSupportNotches':support,'ICR':label(icr),'Audit':'BICRA → Anchor → 4 nhóm yếu tố nội sinh → SACP → hỗ trợ bên ngoài → ICR'}

def securities_rating(ticker,overrides=None):
    s=get_snapshot(ticker);o=overrides or {}
    bank_anchor='a-';anchor=move(bank_anchor,-2)
    bp=o.get('BusinessProfile','Phù Hợp')
    ce=o.get('CapitalEarnings',_relative(s.get('ROE'),_industry_mean(ticker,'ROE')))
    rp=o.get('RiskPosition','Phù Hợp')
    fl=o.get('FundingLiquidity',_relative(s.get('CurrentRatio'),_industry_mean(ticker,'CurrentRatio')))
    factors={'Hồ sơ Kinh doanh':bp,'Vốn và Lợi nhuận':ce,'Vị thế Rủi ro':rp,'Nguồn vốn và Thanh khoản':fl}
    notches=sum(NOTCH.get(v,0) for v in factors.values())
    sacp=move(anchor,notches)
    if SCALE.index(sacp)>SCALE.index('b-') and not o.get('DefaultScenario',False):sacp='b-'
    if o.get('DefaultScenario',False):sacp='ccc'
    support=int(o.get('ExternalSupportNotches',0));icr=move(sacp,support)
    return {'Methodology':'SECURITIES','MethodologyName':'Phương pháp XHTN Công ty Chứng khoán','BICRAReference':label(bank_anchor),'SectorAnchorAdjustment':-2,'Anchor':label(anchor),'Factors':factors,'InternalNotches':notches,'SACP':label(sacp),'ExternalSupportNotches':support,'ICR':label(icr),'Audit':'BICRA tham chiếu → -2 bậc Anchor CTCK → 4 nhóm yếu tố nội sinh → SACP → hỗ trợ → ICR'}

# -------- Corporate methodology --------
# The corporate sample methodology is risk-factor based: macro/industry, business,
# financial, governance, then liquidity/modifiers/support. Quantitative automation
# must use company + peer evidence and must NOT fabricate a rating when data are absent.

def _peer_frame(ticker):
    try:
        from scripts.sector_benchmark_engine import industry_snapshot
        z=industry_snapshot(ticker)
        return z if z is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def _enrich(d):
    try:
        from scripts.methodology_kpi_engine import enrich_row
        return enrich_row(d)
    except Exception:
        return dict(d)

def _risk_from_percentile(value, series, higher_better=True):
    v=num(value)
    x=pd.to_numeric(series,errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
    if v is None or len(x)<3:return None
    # percentile of target within peer distribution
    pct=float((x<=v).mean())
    goodness=pct if higher_better else 1-pct
    # 1 = lowest risk / strongest, 6 = highest risk / weakest
    return float(np.clip(6-5*goodness,1,6))

def _dimension_score(s, peers, specs):
    vals=[]; evidence=[]
    for metric,weight,higher_better in specs:
        if metric not in peers.columns: continue
        r=_risk_from_percentile(s.get(metric),peers[metric],higher_better)
        if r is None: continue
        vals.append((r,weight)); evidence.append(metric)
    if not vals:return None,[],0.0
    w=sum(x[1] for x in vals)
    return sum(r*wt for r,wt in vals)/w,evidence,w

def _risk_label(score):
    if score is None:return 'Chưa đủ dữ liệu'
    if score<1.75:return 'Rất Thấp'
    if score<2.75:return 'Thấp'
    if score<3.75:return 'Trung Bình'
    if score<4.75:return 'Đáng Kể'
    if score<5.5:return 'Cao'
    return 'Rất Cao'

def _liq_label(score):
    if score is None:return 'Chưa đủ dữ liệu'
    if score<1.8:return 'Rất Mạnh'
    if score<2.6:return 'Mạnh'
    if score<3.4:return 'Phù Hợp'
    if score<4.2:return 'Trung Bình'
    return 'Yếu'

def _anchor_from_weighted(x):
    # Transparent model mapping for simulation, not a claim of an official CRA table.
    if x<=1.75:return 'a+'
    if x<=2.25:return 'a'
    if x<=2.75:return 'a-'
    if x<=3.25:return 'bbb+'
    if x<=3.75:return 'bbb'
    if x<=4.25:return 'bbb-'
    if x<=4.75:return 'bb+'
    if x<=5.25:return 'bb'
    return 'bb-'

def corporate_rating(ticker,overrides=None):
    o=overrides or {}; meta=get_company(ticker)
    raw=get_snapshot(ticker); s=_enrich(raw)
    peers=_peer_frame(ticker)
    if len(peers): peers=pd.DataFrame([_enrich(r) for r in peers.to_dict('records')])

    # Four business factors mirror the sample report logic: competitive position/scale,
    # operating efficiency, profitability and diversification/quality of growth.
    business_specs=[
        ('Revenue',.18,True),('TotalAssets',.12,True),('AssetTurnover',.18,True),
        ('GrossMargin',.18,True),('EBITDAMargin',.20,True),('ROA',.14,True)]
    financial_specs=[
        ('DebtEquity',.15,False),('NetDebtEBITDA',.20,False),('DebtEBITDA',.15,False),
        ('CFO_Debt',.18,True),('FOCF_Debt',.12,True),('CurrentRatio',.10,True),('CashDebt',.10,True)]
    liquidity_specs=[('CurrentRatio',.35,True),('CashDebt',.25,True),('CFO_Debt',.25,True),('FOCF_Debt',.15,True)]

    b_auto,b_ev,b_cov=_dimension_score(s,peers,business_specs)
    f_auto,f_ev,f_cov=_dimension_score(s,peers,financial_specs)
    l_auto,l_ev,l_cov=_dimension_score(s,peers,liquidity_specs)

    industry=float(o.get('IndustryRisk',3.0))  # analyst/public-intelligence input; neutral if not overridden
    business=float(o.get('BusinessRisk',b_auto)) if o.get('BusinessRisk',b_auto) is not None else None
    financial=float(o.get('FinancialRisk',f_auto)) if o.get('FinancialRisk',f_auto) is not None else None
    governance=float(o.get('GovernanceRisk',3.0)) # qualitative; neutral until evidence/analyst override
    liquidity=float(o.get('LiquidityScore',l_auto)) if o.get('LiquidityScore',l_auto) is not None else None

    peer_count=max(0,len(peers)-1 if len(peers) and 'Ticker' in peers and str(ticker).upper() in set(peers.Ticker.astype(str).str.upper()) else len(peers))
    core_available=sum(x is not None for x in [business,financial])
    evidence_metrics=sorted(set(b_ev+f_ev+l_ev))
    quant_coverage=min(1.0,(b_cov+f_cov)/(1.0+1.0)) # specs each sum ~1
    sufficient=(core_available==2 and peer_count>=3 and len(evidence_metrics)>=5)

    risk_scores={'Rủi ro Vĩ mô và Ngành':industry,
                 'Rủi ro Kinh doanh':business if business is not None else np.nan,
                 'Rủi ro Tài chính':financial if financial is not None else np.nan,
                 'Rủi ro Quản trị và Quản lý':governance}
    risk_labels={k:_risk_label(v if np.isfinite(v) else None) for k,v in risk_scores.items()}

    # Sample-report-consistent weighting: business and financial profiles carry most of the quantitative signal.
    # This is explicitly a simulation layer and can be overridden by analysts/committee.
    w=o.get('Weights',{'IndustryRisk':.20,'BusinessRisk':.30,'FinancialRisk':.35,'GovernanceRisk':.15})
    if not sufficient and 'AnchorOverride' not in o:
        return {
            'Methodology':'CORPORATE','MethodologyName':'Phương pháp XHTN Doanh nghiệp phi tài chính',
            'RiskScores':risk_scores,'RiskLabels':risk_labels,'Weights':w,'WeightedScore':None,
            'Anchor':'N/A','ModifierNotches':0,'SCA':'N/A','Liquidity':_liq_label(liquidity),
            'LiquidityScore':liquidity,'ExternalSupportNotches':int(o.get('ExternalSupportNotches',0)),
            'ICR':'N/A','Outlook':'N/A','PeerCount':peer_count,'EvidenceMetrics':evidence_metrics,
            'QuantCoverage':quant_coverage,'DataSufficientForAutoRating':False,
            'ProvisionalAutoScoring':True,
            'Audit':'Chưa phát hành bậc mô phỏng: cần tối thiểu dữ liệu kinh doanh + tài chính và >=3 peer có dữ liệu. Rủi ro ngành/quản trị là judgment cần chuyên viên xác nhận.'}

    weighted=(industry*w.get('IndustryRisk',0)+business*w.get('BusinessRisk',0)+
              financial*w.get('FinancialRisk',0)+governance*w.get('GovernanceRisk',0))
    if 'AnchorOverride' in o: anchor=str(o['AnchorOverride']).lower().replace('vn','')
    else: anchor=_anchor_from_weighted(weighted)

    modifier=int(o.get('ModifierNotches',0)); sca=move(anchor,modifier)
    # Governance/liquidity caps are applied only when supported by an explicit high-risk score.
    if governance>=5 and SCALE.index(sca)<SCALE.index('bb-'):sca='bb-'
    if liquidity is not None and liquidity>=4.5 and SCALE.index(sca)<SCALE.index('b+'):sca='b+'
    support=int(o.get('ExternalSupportNotches',0)); icr=move(sca,support)
    return {
        'Methodology':'CORPORATE','MethodologyName':'Phương pháp XHTN Doanh nghiệp phi tài chính',
        'RiskScores':risk_scores,'RiskLabels':risk_labels,'Weights':w,'WeightedScore':weighted,
        'Anchor':label(anchor),'ModifierNotches':modifier,'SCA':label(sca),
        'Liquidity':_liq_label(liquidity),'LiquidityScore':liquidity,
        'ExternalSupportNotches':support,'ICR':label(icr),'Outlook':o.get('Outlook','Ổn định'),
        'PeerCount':peer_count,'EvidenceMetrics':evidence_metrics,'QuantCoverage':quant_coverage,
        'DataSufficientForAutoRating':True,'ProvisionalAutoScoring':True,
        'Audit':'Rủi ro vĩ mô & ngành → Rủi ro kinh doanh (peer/hiệu quả/sinh lợi) → Rủi ro tài chính (đòn bẩy/dòng tiền/trả nợ) → Quản trị → Thanh khoản/modifiers → SCA → hỗ trợ → ICR. Điểm định tính cần analyst validation.'}

def rate_company(ticker,overrides=None):
    m=get_company(ticker);typ=str(m.get('EntityType','CORPORATE'))
    method=str(m.get('Methodology',''))
    if method=='EXCLUDED_SPECIALIZED':
        return {'Methodology':'EXCLUDED_SPECIALIZED','MethodologyName':'Ngoài phạm vi phương pháp doanh nghiệp thông thường','ICR':'N/A','Audit':'Cần phương pháp chuyên biệt; không tự động XHTN.'}
    if typ=='BANK':return bank_rating(ticker,overrides)
    if typ=='SECURITIES':return securities_rating(ticker,overrides)
    return corporate_rating(ticker,overrides)
