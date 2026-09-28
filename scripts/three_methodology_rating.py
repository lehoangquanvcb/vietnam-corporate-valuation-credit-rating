import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
import numpy as np
import pandas as pd
from pathlib import Path
import csv
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
    # Display/output convention: rating grades do not use the historical 'vn' prefix.
    x=str(x).lower().replace('vn','')
    return x.upper()

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

def _bank_franchise_profile(ticker):
    path=Path(__file__).resolve().parents[1]/'data'/'bank_franchise_master.csv'
    if not path.exists(): return {}
    try:
        with path.open('r',encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                if str(row.get('Ticker','')).upper().strip()==str(ticker).upper().strip(): return row
    except Exception: pass
    return {}

def _bank_master_score(row,key):
    try: return float(np.clip(float(row.get(key,'')),1,6))
    except Exception: return None

def _bank_business_overlay(quant_score, profile):
    brand=_bank_master_score(profile,'BrandFranchiseScore')
    role=_bank_master_score(profile,'SystemRoleScore')
    vals=[]
    if quant_score is not None: vals.append((float(quant_score),.70))
    if brand is not None: vals.append((brand,.20))
    if role is not None: vals.append((role,.10))
    if not vals:return quant_score,[]
    score=sum(v*w for v,w in vals)/sum(w for _,w in vals)
    notes=[]
    if brand is not None: notes.append(f"Uy tín/thương hiệu: {brand:.2f}/6")
    if role is not None: notes.append(f"Vai trò hệ thống: {role:.2f}/6")
    leading_private=str(profile.get('LeadingPrivateBank','')).strip().lower() in ('1','true','yes','y')
    efficient_small=str(profile.get('EfficientSmallBank','')).strip().lower() in ('1','true','yes','y')
    # Optional auditable component cap from master. This is NOT a final-rating override:
    # it only constrains the component when the issuer has been independently
    # classified as a verified leading franchise.
    try:
        bp_cap=float(profile.get('BusinessProfileScoreCap',''))
    except Exception:
        bp_cap=None
    if (leading_private or efficient_small) and bp_cap is not None and score>bp_cap:
        score=bp_cap
        notes.append(f'Calibration franchise đã xác minh: giới hạn điểm Hồ sơ Kinh doanh ở {bp_cap:.2f}/6')
    return float(np.clip(score,1,6)),notes

def _bank_ce_calibration(score, snap, profile):
    if score is None:return None,[]
    x=float(score); notes=[]
    strategic=str(profile.get('StrategicStateBank','')).strip().lower() in ('1','true','yes','y')
    leading_private=str(profile.get('LeadingPrivateBank','')).strip().lower() in ('1','true','yes','y')
    car=_bank_ratio(snap.get('CAR'))
    npl=_bank_ratio(snap.get('NPL'))
    casa=_bank_ratio(snap.get('CASA'))
    if strategic and car is not None and car>=0.10:
        if x>2.35:
            x=2.35; notes.append('Vai trò NHTM nhà nước chiến lược + CAR >=10%: hiệu chỉnh về vùng Mạnh')
        elif x<1.65:
            x=1.65; notes.append('Yêu cầu vốn/lợi nhuận vượt trội để đạt Rất Mạnh; hiệu chỉnh về vùng Mạnh')
    if leading_private and car is not None and car>=0.14:
        quality_ok=(npl is None or npl<=0.015)
        funding_ok=(casa is None or casa>=0.30)
        if quality_ok and funding_ok:
            try:
                ce_cap=float(profile.get('CapitalEarningsScoreCap',''))
            except Exception:
                ce_cap=2.35
            if x>ce_cap:
                x=ce_cap; notes.append(f'Ngân hàng tư nhân dẫn đầu + CAR/NPL/CASA đạt điều kiện: giới hạn điểm Vốn & Lợi nhuận ở {ce_cap:.2f}/6')
            if x<1.65:
                x=1.65; notes.append('Không tự động xếp Rất Mạnh; yêu cầu vốn/lợi nhuận vượt trội bền vững')
    return float(np.clip(x,1,6)),notes

def _bank_peer_frame(ticker):
    """Bank peer snapshot used only for BANK methodology calibration."""
    try:
        from scripts.sector_benchmark_engine import industry_snapshot
        z=industry_snapshot(ticker)
        if z is None:
            return pd.DataFrame()
        z=pd.DataFrame(z).copy()
        if 'Ticker' in z.columns:
            # Keep the target in the distribution only once; percentile remains sector-relative.
            z=z.drop_duplicates(subset=['Ticker'], keep='last')
        return z
    except Exception:
        return pd.DataFrame()

def _bank_pct_score(value, series, higher_better=True):
    """Continuous 1–6 risk score. 1 = strongest, 6 = weakest."""
    v=num(value)
    x=pd.to_numeric(series,errors='coerce').replace([np.inf,-np.inf],np.nan).dropna()
    if v is None or len(x)<5:
        return None
    pct=float((x<=v).mean())
    goodness=pct if higher_better else 1-pct
    return float(np.clip(6-5*goodness,1,6))

def _bank_dimension(s, peers, specs):
    vals=[]; details=[]
    for metric,weight,higher_better in specs:
        if metric not in peers.columns:
            continue
        score=_bank_pct_score(s.get(metric),peers[metric],higher_better)
        if score is None:
            continue
        vals.append((score,float(weight)))
        details.append({'Metric':metric,'Score':score,'Weight':float(weight),
                        'HigherBetter':bool(higher_better)})
    if not vals:
        return None,details
    den=sum(w for _,w in vals)
    return sum(score*w for score,w in vals)/den,details

def _bank_assessment(score):
    """Assessment buckets calibrated to avoid compression around 3/6."""
    if score is None:
        return 'Phù Hợp'
    x=float(score)
    if x<=1.65:return 'Rất Mạnh'
    if x<=2.35:return 'Mạnh'
    if x<=3.65:return 'Phù Hợp'
    if x<=4.50:return 'Trung Bình'
    if x<=5.25:return 'Yếu'
    return 'Rất Yếu'

def _bank_ratio(v):
    """Normalize percentage-like values whether stored as 0.111 or 11.1."""
    x=num(v)
    if x is None:
        return None
    x=float(x)
    return x/100.0 if abs(x)>1.5 else x

def _bank_capital_guardrail(score, s):
    """Absolute capital guardrail layered on peer-relative Capital & Earnings.
    It prevents a weakly capitalised bank from scoring strongly merely because
    the whole peer set is weak. Strong capital can modestly improve the score.
    """
    if score is None:
        return None, []
    x=float(score); notes=[]
    car=_bank_ratio(s.get('CAR'))
    eq=_bank_ratio(s.get('EquityAssets'))
    if car is not None:
        if car>=0.14:
            x-=0.35; notes.append('CAR >=14%: hỗ trợ')
        elif car>=0.12:
            x-=0.15; notes.append('CAR 12%-14%: hỗ trợ nhẹ')
        elif car<0.08:
            x=max(x,5.25); notes.append('CAR <8%: giới hạn ở mức Yếu/Rất Yếu')
        elif car<0.09:
            x=max(x,4.75); notes.append('CAR 8%-9%: giới hạn ở mức Yếu')
        elif car<0.105:
            x=max(x,4.00); notes.append('CAR 9%-10,5%: hạn chế đánh giá')
    if eq is not None and eq<0.045:
        x=max(x,4.25); notes.append('VCSH/TTS <4,5%: bộ đệm vốn mỏng')
    return float(np.clip(x,1,6)),notes

def bank_rating(ticker, overrides=None):
    """BANK methodology V8.90.

    BICRA/Anchor remains the common banking-sector starting point.
    Entity differentiation is generated from four bank-specific components.
    Business Profile and Capital & Earnings now use multi-metric, peer-relative
    continuous scores instead of a single ROE comparison / manual neutral value.
    """
    s=get_snapshot(ticker); o=overrides or {}
    peers=_bank_peer_frame(ticker)
    anchor=str(o.get('AnchorOverride','a-')).lower().replace('vn','')

    # 1) Business Profile: franchise/scale is deliberately prominent.
    # The target is compared with listed/registered bank peers rather than using
    # one broad absolute size bucket.
    bp_specs=[
        ('TotalAssets',.40,True),
        ('GrossLoans',.25,True),
        ('CustomerDeposits',.25,True),
        ('CASA',.10,True),
    ]
    bp_score,bp_detail=_bank_dimension(s,peers,bp_specs)
    franchise=_bank_franchise_profile(ticker)
    bp_score,bp_overlay_notes=_bank_business_overlay(bp_score,franchise)

    # 2) Capital & Earnings: loss-absorption capacity first, profitability second.
    # CAR receives the largest weight and an additional absolute guardrail.
    ce_specs=[
        ('CAR',.35,True),
        ('EquityAssets',.15,True),
        ('ROE',.15,True),
        ('ROA',.10,True),
        ('NIM',.10,True),
        ('CIR',.05,False),
        ('ProfitAssets',.10,True),
    ]
    ce_score,ce_detail=_bank_dimension(s,peers,ce_specs)
    ce_score,ce_guardrails=_bank_capital_guardrail(ce_score,s)
    ce_score,ce_calibration_notes=_bank_ce_calibration(ce_score,s,franchise)
    ce_guardrails=(ce_guardrails or [])+(ce_calibration_notes or [])

    # Risk Position and Funding/Liquidity retain the existing bank methodology
    # bridge for compatibility, but use a continuous component score when peers
    # are available so the final notch bridge is more discriminating.
    rp_specs=[('NPL',.70,False),('CreditCostProxy',.30,False)]
    fl_specs=[('CASA',.50,True),('LDR',.30,False),('DepositAssets',.20,True)]
    rp_score,rp_detail=_bank_dimension(s,peers,rp_specs)
    fl_score,fl_detail=_bank_dimension(s,peers,fl_specs)

    # V8.93: data-quality / franchise calibration for verified leading private banks.
    # These are component-level ceilings stored in an auditable master, not final-rating overrides.
    leading_private=str(franchise.get('LeadingPrivateBank','')).strip().lower() in ('1','true','yes','y')
    efficient_small=str(franchise.get('EfficientSmallBank','')).strip().lower() in ('1','true','yes','y')
    if leading_private or efficient_small:
        try:
            rp_cap=float(franchise.get('RiskPositionScoreCap',''))
        except Exception:
            rp_cap=None
        try:
            fl_cap=float(franchise.get('FundingLiquidityScoreCap',''))
        except Exception:
            fl_cap=None
        if rp_cap is not None and rp_score is not None and rp_score>rp_cap:
            rp_score=rp_cap
            rp_detail=(rp_detail or [])+[{'Metric':'QualitativeCalibration','Score':rp_cap,'Weight':0,
                                         'HigherBetter':True,'Note':'Verified leading-private-bank Risk Position cap'}]
        if fl_cap is not None and fl_score is not None and fl_score>fl_cap:
            fl_score=fl_cap
            fl_detail=(fl_detail or [])+[{'Metric':'QualitativeCalibration','Score':fl_cap,'Weight':0,
                                         'HigherBetter':True,'Note':'Verified leading-private-bank Funding/Liquidity cap'}]

    # Fallbacks preserve operation when a peer metric is unavailable.
    bp=o.get('BusinessProfile', _bank_assessment(bp_score) if bp_score is not None else 'Phù Hợp')
    ce=o.get('CapitalEarnings', _bank_assessment(ce_score) if ce_score is not None
             else _relative(s.get('ROE'),_industry_mean(ticker,'ROE')))
    rp=o.get('RiskPosition', _bank_assessment(rp_score) if rp_score is not None
             else _relative(s.get('NPL'),_industry_mean(ticker,'NPL'),lower=True))
    fl=o.get('FundingLiquidity', _bank_assessment(fl_score) if fl_score is not None
             else _relative(s.get('CASA'),_industry_mean(ticker,'CASA')))

    factors={'Hồ sơ Kinh doanh':bp,'Vốn và Lợi nhuận':ce,
             'Vị thế Rủi ro':rp,'Huy động vốn và Thanh khoản':fl}
    factor_scores={'Hồ sơ Kinh doanh':bp_score,'Vốn và Lợi nhuận':ce_score,
                   'Vị thế Rủi ro':rp_score,'Huy động vốn và Thanh khoản':fl_score}
    factor_details={'Hồ sơ Kinh doanh':bp_detail,'Vốn và Lợi nhuận':ce_detail,
                    'Vị thế Rủi ro':rp_detail,'Huy động vốn và Thanh khoản':fl_detail}

    notches=sum(NOTCH.get(v,0) for v in factors.values())
    sacp=move(anchor,notches)
    support=int(o.get('ExternalSupportNotches',0)); icr=move(sacp,support)

    return {
        'Methodology':'BANK','MethodologyName':'Phương pháp XHTN Ngân hàng',
        'BICRA':label(anchor),'Anchor':label(anchor),
        'Factors':factors,'FactorScores':factor_scores,'FactorDetails':factor_details,
        'CapitalGuardrails':ce_guardrails,
        'BusinessProfileOverlayNotes':bp_overlay_notes,
        'StateOwnershipPct':franchise.get('StateOwnershipPct',''),
        'StrategicStateBank':franchise.get('StrategicStateBank',''),
        'LeadingPrivateBank':franchise.get('LeadingPrivateBank',''),
        'EfficientSmallBank':franchise.get('EfficientSmallBank',''),
        'BusinessProfileScoreCap':franchise.get('BusinessProfileScoreCap',''),
        'CapitalEarningsScoreCap':franchise.get('CapitalEarningsScoreCap',''),
        'RiskPositionScoreCap':franchise.get('RiskPositionScoreCap',''),
        'FundingLiquidityScoreCap':franchise.get('FundingLiquidityScoreCap',''),
        'FranchiseSource':franchise.get('Source',''),
        'FranchiseSourceDate':franchise.get('SourceDate',''),
        'InternalNotches':notches,'SACP':label(sacp),
        'ExternalSupportNotches':support,'ICR':label(icr),
        'PeerCount':int(len(peers)),
        'Audit':'BICRA → Anchor → Hồ sơ Kinh doanh (70% định lượng + 20% uy tín/thương hiệu + 10% vai trò hệ thống) → '
                'Vốn & Lợi nhuận (CAR/bộ đệm vốn + khả năng sinh lời, có absolute guardrail) → '
                'Vị thế Rủi ro → Huy động vốn & Thanh khoản → SACP → hỗ trợ bên ngoài → ICR'
    }

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
    # 17-notch 1–6 corporate score ladder supplied by the user.
    # The published score points are treated as representative notch points;
    # midpoint cutoffs map any continuous weighted score to the nearest notch.
    try:
        x=float(x)
    except Exception:
        return 'N/A'
    if x<=1.155:return 'aaa'
    if x<=1.470:return 'aa+'
    if x<=1.785:return 'aa'
    if x<=2.095:return 'aa-'
    if x<=2.405:return 'a+'
    if x<=2.720:return 'a'
    if x<=3.035:return 'a-'
    if x<=3.345:return 'bbb+'
    if x<=3.655:return 'bbb'
    if x<=3.970:return 'bbb-'
    if x<=4.285:return 'bb+'
    if x<=4.595:return 'bb'
    if x<=4.905:return 'bb-'
    if x<=5.220:return 'b+'
    if x<=5.535:return 'b'
    if x<=5.845:return 'b-'
    # Engine SCALE has ccc/cc/c not a combined "ccc-c" notch.
    # Use ccc as the operational anchor for the terminal vnCCC-vnC score bucket;
    # downstream default-scenario analysis can distinguish ccc/cc/c if required.
    return 'ccc'

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
        'Audit':'Rủi ro vĩ mô & ngành → Rủi ro kinh doanh → Rủi ro tài chính → Quản trị → điểm tổng hợp có trọng số (1–6) → quy đổi Anchor theo thang 17 bậc → Thanh khoản/modifiers → SCA → hỗ trợ → ICR. Điểm định tính cần analyst validation.'}

def rate_company(ticker,overrides=None):
    m=get_company(ticker);typ=str(m.get('EntityType','CORPORATE'))
    method=str(m.get('Methodology',''))
    if method=='EXCLUDED_SPECIALIZED':
        return {'Methodology':'EXCLUDED_SPECIALIZED','MethodologyName':'Ngoài phạm vi phương pháp doanh nghiệp thông thường','ICR':'N/A','Audit':'Cần phương pháp chuyên biệt; không tự động XHTN.'}
    if typ=='BANK':return bank_rating(ticker,overrides)
    if typ=='SECURITIES':return securities_rating(ticker,overrides)
    return corporate_rating(ticker,overrides)
