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
    if v is None or b in (None,0):return None
    gap=v/b-1
    if lower:gap=-gap
    if gap>=.30:return 'Rất Mạnh'
    if gap>=.10:return 'Mạnh'
    if gap<=-.35:return 'Yếu'
    if gap<=-.15:return 'Trung Bình'
    return 'Phù Hợp'

def _industry_mean(ticker,metric):
    from scripts.methodology_kpi_engine import methodology_kpi_table
    z=methodology_kpi_table(ticker)
    q=z[z.Metric.eq(metric)]
    return num(q.iloc[0]['TB ngành']) if len(q) else None

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
    # Các thành phần định tính chưa thẩm định không được mặc định "Phù Hợp".
    o=dict(overrides or {}); anchor=move('a-',-2)
    titles={'BusinessProfile':'Hồ sơ Kinh doanh','CapitalEarnings':'Vốn và Lợi nhuận',
            'RiskPosition':'Vị thế Rủi ro','FundingLiquidity':'Nguồn vốn và Thanh khoản'}
    factors={title:o[key] for key,title in titles.items() if o.get(key) in NOTCH}
    missing={key:'Chưa thẩm định' for key in titles if o.get(key) not in NOTCH}
    support=o.get('ExternalSupportNotches')
    valid=isinstance(support,int) and not isinstance(support,bool) and 0<=support<=8
    if not valid:missing['ExternalSupportNotches']='Chưa thẩm định hỗ trợ bên ngoài'
    complete=len(factors)==4
    adjustment=sum(NOTCH[v] for v in factors.values()) if complete else None
    sacp=move(anchor,adjustment) if complete else None
    return {'Methodology':'SECURITIES','MethodologyName':'Phương pháp XHTN Công ty Chứng khoán',
            'BICRAReference':label('a-'),'SectorAnchorAdjustment':-2,'Anchor':label(anchor),
            'Factors':factors,'InternalNotches':adjustment,'SACP':label(sacp) if sacp else 'N/A',
            'ExternalSupportNotches':support if valid else None,
            'ICR':label(move(sacp,support)) if complete and valid else 'N/A',
            'Outlook':o.get('Outlook','Chưa thẩm định'),'MissingEvidence':missing,
            'DataSufficientForAutoRating':complete and valid,'RatingStatus':'UNREVIEWED' if missing else 'SIMULATION',
            'Audit':'Anchor CTCK bằng A- giảm 2 bậc; đánh giá thành phần và hỗ trợ phải được xác nhận; không tự đặt sàn B-.'}

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
        from scripts.financial_evidence import metric_evidence
        target_ev=metric_evidence(s,metric)
        same=peers.apply(lambda row: metric_evidence(row,metric)['Period']==target_ev['Period'] and metric_evidence(row,metric)['Basis']==target_ev['Basis'],axis=1)
        r=_risk_from_percentile(s.get(metric),peers.loc[same,metric],higher_better)
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

    industry=num(o.get('IndustryRisk'))  # analyst/public-intelligence input; neutral if not overridden
    business=float(o.get('BusinessRisk',b_auto)) if o.get('BusinessRisk',b_auto) is not None else None
    financial=float(o.get('FinancialRisk',f_auto)) if o.get('FinancialRisk',f_auto) is not None else None
    governance=num(o.get('GovernanceRisk')) # qualitative; neutral until evidence/analyst override
    liquidity=float(o.get('LiquidityScore',l_auto)) if o.get('LiquidityScore',l_auto) is not None else None

    peer_count=max(0,len(peers)-1 if len(peers) and 'Ticker' in peers and str(ticker).upper() in set(peers.Ticker.astype(str).str.upper()) else len(peers))
    core_available=sum(x is not None for x in [business,financial])
    evidence_metrics=sorted(set(b_ev+f_ev+l_ev))
    quant_coverage=min(1.0,(b_cov+f_cov)/(1.0+1.0)) # specs each sum ~1
    sufficient=(core_available==2 and peer_count>=3 and len(evidence_metrics)>=5)

    risk_scores={'Rủi ro Vĩ mô và Ngành':industry if industry is not None else np.nan,
                 'Rủi ro Kinh doanh':business if business is not None else np.nan,
                 'Rủi ro Tài chính':financial if financial is not None else np.nan,
                 'Rủi ro Quản trị và Quản lý':governance if governance is not None else np.nan}
    risk_labels={k:_risk_label(v if np.isfinite(v) else None) for k,v in risk_scores.items()}

    # Sample-report-consistent weighting: business and financial profiles carry most of the quantitative signal.
    # This is explicitly a simulation layer and can be overridden by analysts/committee.
    w=o.get('Weights',{'IndustryRisk':.20,'BusinessRisk':.30,'FinancialRisk':.35,'GovernanceRisk':.15})
    if set(w)!={'IndustryRisk','BusinessRisk','FinancialRisk','GovernanceRisk'} or any(num(v) is None or v<0 for v in w.values()) or abs(sum(w.values())-1)>1e-8:
        raise ValueError('Trọng số phải không âm và tổng bằng 1')
    missing={}
    for key,value in [('IndustryRisk',industry),('BusinessRisk',business),('FinancialRisk',financial),('GovernanceRisk',governance)]:
        if value is None:missing[key]='Chưa thẩm định' if key in ('IndustryRisk','GovernanceRisk') else 'Thiếu dữ liệu/peer'
        elif not 1<=value<=6:raise ValueError(key+': điểm phải trong khoảng 1..6')
    for key,lo,hi in [('ModifierNotches',-6,6),('ExternalSupportNotches',0,8)]:
        v=o.get(key)
        if not isinstance(v,int) or isinstance(v,bool) or not lo<=v<=hi:missing[key]='Chưa thẩm định'
    if not sufficient:missing['QuantitativeEvidence']='Chưa đủ chỉ tiêu và ít nhất 3 peer'
    if missing:
        return {
            'Methodology':'CORPORATE','MethodologyName':'Phương pháp XHTN Doanh nghiệp phi tài chính',
            'RiskScores':risk_scores,'RiskLabels':risk_labels,'Weights':w,'WeightedScore':None,
            'Anchor':'N/A','ModifierNotches':o.get('ModifierNotches'),'SCA':'N/A','Liquidity':_liq_label(liquidity),
            'LiquidityScore':liquidity,'ExternalSupportNotches':o.get('ExternalSupportNotches'),
            'ICR':'N/A','Outlook':'Chưa thẩm định','PeerCount':peer_count,'EvidenceMetrics':evidence_metrics,
            'QuantCoverage':quant_coverage,'DataSufficientForAutoRating':False,
            'ProvisionalAutoScoring':True,'MissingEvidence':missing,'RatingStatus':'UNREVIEWED',
            'Audit':'Điểm kinh doanh/tài chính là tín hiệu định lượng; ngành, quản trị, modifiers và hỗ trợ phải được thẩm định trước khi hình thành bậc mô phỏng.'}

    weighted=(industry*w.get('IndustryRisk',0)+business*w.get('BusinessRisk',0)+
              financial*w.get('FinancialRisk',0)+governance*w.get('GovernanceRisk',0))
    anchor=_anchor_from_weighted(weighted)

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



"""Bank rating methodology patch V8.75.1.

Integration: replace the existing scripts/three_methodology_rating.py bank_rating()
with bank_rating_v875(), or alias bank_rating=bank_rating_v875 after the original
bank_rating definition. Requires original module's get_snapshot, num, move,
label, NOTCH, _industry_mean, and SCALE. No network/API calls.

No arbitrary AAA overrides. Fixed A- anchor retained. External support must be
explicitly assessed and supplied by the analyst; never inferred from ticker.
"""
import math

BANK_FACTOR_SPEC = {
    'CapitalEarnings': [('CAR', .30, True), ('ROA', .25, True), ('ROE', .20, True), ('NIM', .15, True), ('CIR', .10, False)],
    'RiskPosition': [('NPL', .35, False), ('LoanLossCoverage', .30, True), ('CreditCost', .20, False), ('Group2LoansRatio', .15, False)],
    'FundingLiquidity': [('CASA', .30, True), ('LDR', .25, False), ('LiquidityCoverageRatio', .25, True), ('StableFundingRatio', .20, True)],
}

def _bank_numeric(x):
    try:
        v = num(x)
        return float(v) if v is not None and math.isfinite(float(v)) else None
    except (TypeError, ValueError, OverflowError):
        return None

def _bank_peer_gap(v, benchmark, higher_better=True):
    """Robust symmetric relative comparison; negative/zero peer means are not comparable."""
    a, b = _bank_numeric(v), _bank_numeric(benchmark)
    if a is None or b is None or b <= 0 or a < 0:
        return None
    delta = (a - b) / max(abs(a), abs(b), 1e-12)
    if not higher_better:
        delta = -delta
    if delta >= .25: return 'Rất Mạnh'
    if delta >= .10: return 'Mạnh'
    if delta <= -.25: return 'Yếu'
    if delta <= -.10: return 'Trung Bình'
    return 'Phù Hợp'

def _bank_factor_score(ticker, snapshot, spec, minimum=2, benchmarks=None):
    observations=[]; missing=[]
    for metric, weight, higher_better in spec:
        actual = _bank_numeric(snapshot.get(metric))
        benchmark = _bank_numeric((benchmarks or {}).get(metric))
        grade = _bank_peer_gap(actual, benchmark, higher_better)
        if grade is None:
            missing.append({'Metric':metric, 'Actual':actual, 'PeerMean':benchmark, 'Reason':'Thiếu dữ liệu hoặc benchmark không hợp lệ'})
        else:
            observations.append({'Metric':metric,'Actual':actual,'PeerMean':benchmark,'Grade':grade,'Weight':weight,'Notches':NOTCH[grade]})
    if len(observations)<minimum:
        return None, observations, missing
    denom=sum(x['Weight'] for x in observations)
    avg=sum(x['Weight']*x['Notches'] for x in observations)/denom
    # One score per factor; avoid summing notch adjustments for individual metrics.
    grade=min(NOTCH, key=lambda k: abs(NOTCH[k]-avg))
    return grade, observations, missing

def bank_rating_v875(ticker, overrides=None):
    o=overrides or {}; s=get_snapshot(ticker); anchor='a-'
    from scripts.methodology_kpi_engine import methodology_kpi_table
    kt=methodology_kpi_table(ticker)
    benchmarks=dict(zip(kt.Metric,kt['TB ngành']))
    # Business position cannot be assessed using ROE/NPL/CASA; analyst validation required.
    business=o.get('BusinessProfile')
    factors={}; evidence={}; missing={}
    if business in NOTCH:
        factors['Hồ sơ Kinh doanh']=business
    else:
        missing['BusinessProfile']='Chưa có đánh giá quy mô, thị phần, đa dạng hóa, vai trò hệ thống'
    for key, title in [('CapitalEarnings','Vốn và Lợi nhuận'),('RiskPosition','Vị thế Rủi ro'),('FundingLiquidity','Huy động vốn và Thanh khoản')]:
        grade, obs, absent=_bank_factor_score(ticker,s,BANK_FACTOR_SPEC[key],benchmarks=benchmarks)
        if o.get(key) in NOTCH:
            grade=o[key]
        if grade is not None: factors[title]=grade
        else: missing[key]='Chưa đủ >=2 chỉ tiêu có dữ liệu và benchmark hợp lệ'
        evidence[key]=obs
        if absent: missing[key+'_metrics']=absent
    # Do not treat unavailable factors as neutral. No auto-rating if evidence insufficient.
    complete=len(factors)==4
    support=o.get('ExternalSupportNotches')
    support_valid=isinstance(support,int) and not isinstance(support,bool) and 0<=support<=8
    if not support_valid:missing['ExternalSupportNotches']='Chưa thẩm định hỗ trợ bên ngoài'
    sacp=move(anchor,sum(NOTCH[v] for v in factors.values())) if complete else None
    icr=move(sacp,support) if complete and support_valid else None
    return {'Methodology':'BANK','MethodologyName':'Phương pháp XHTN Ngân hàng – đa chỉ tiêu, thẩm định',
            'BICRA':label(anchor),'Anchor':label(anchor),'Factors':factors,
            'InternalNotches':sum(NOTCH[v] for v in factors.values()) if complete else None,
            'SACP':label(sacp) if sacp else 'N/A',
            'ExternalSupportNotches':support if support_valid else None,
            'ICR':label(icr) if icr else 'N/A',
            'DataSufficientForAutoRating':complete and support_valid,
            'EvidenceByFactor':evidence,'MissingEvidence':missing,'RatingStatus':'SIMULATION' if complete and support_valid else 'UNREVIEWED','Outlook':o.get('Outlook','Chưa thẩm định'),
            'Audit':'Anchor cố định A-; 4 cấu phần đa chỉ tiêu; hỗ trợ ngoài phải có thẩm định; không tự động gán AAA.'}


from scripts.insurance_rating import insurance_rating

def _is_insurance(meta):
    """Recognize insurer from explicit metadata; no inference from ticker alone."""
    typ=str(meta.get('EntityType','')).strip().upper()
    method=str(meta.get('Methodology','')).strip().upper()
    sector=str(meta.get('Sector','')).strip().lower()
    if typ in ('INSURANCE','INSURER','INSURANCE_NONLIFE','INSURANCE_LIFE') or method.startswith('INSURANCE'):
        return True
    return any(x in sector for x in ('bảo hiểm','bao hiem','insurance')) and not any(x in sector for x in ('môi giới','moi gioi','broker'))

def rate_company(ticker,overrides=None):
    m=get_company(ticker); typ=str(m.get('EntityType','CORPORATE')).strip().upper()
    method=str(m.get('Methodology','')).strip().upper()
    if _is_insurance(m):
        return insurance_rating(ticker,overrides)
    if typ=='BANK':
        return bank_rating_v875(ticker,overrides)
    if typ=='SECURITIES':
        return securities_rating(ticker,overrides)
    if method=='EXCLUDED_SPECIALIZED':
        return {'Methodology':'EXCLUDED_SPECIALIZED','MethodologyName':'Chưa có phương pháp phù hợp','ICR':'N/A','Audit':'Không áp dụng phương pháp doanh nghiệp thông thường cho loại hình chuyên biệt.'}
    return corporate_rating(ticker,overrides)

# Compatibility: fixed Anchor A- and evidence gate for every bank caller.
bank_rating = bank_rating_v875
