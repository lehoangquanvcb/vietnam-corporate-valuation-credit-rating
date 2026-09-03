import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from pathlib import Path
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

def _pct(v): return None if num(v) is None else num(v)

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
    except:pass
    return None

def bank_rating(ticker, overrides=None):
    s=get_snapshot(ticker); o=overrides or {}
    # Official methodology: BICRA a- -> bank Anchor. Four internal factor groups.
    anchor='a-'
    bp=o.get('BusinessProfile','Phù Hợp')
    ce=o.get('CapitalEarnings',_relative(s.get('ROE'),_industry_mean(ticker,'ROE')))
    rp=o.get('RiskPosition',_relative(s.get('NPL'),_industry_mean(ticker,'NPL'),lower=True))
    fl=o.get('FundingLiquidity',_relative(s.get('CASA'),_industry_mean(ticker,'CASA')))
    factors={'Hồ sơ Kinh doanh':bp,'Vốn và Lợi nhuận':ce,'Vị thế Rủi ro':rp,'Huy động vốn và Thanh khoản':fl}
    # Auto engine uses conservative end of weak ranges; analyst can override factor/notch.
    notches=sum(NOTCH.get(v,0) for v in factors.values())
    sacp=move(anchor,notches)
    support=int(o.get('ExternalSupportNotches',0));icr=move(sacp,support)
    return {'Methodology':'BANK','MethodologyName':'Phương pháp XHTN Ngân hàng','BICRA':'a-','Anchor':label(anchor),'Factors':factors,'InternalNotches':notches,'SACP':label(sacp),'ExternalSupportNotches':support,'ICR':label(icr),'Audit':'BICRA → Anchor → 4 nhóm yếu tố nội sinh → SACP → hỗ trợ bên ngoài → ICR'}

def securities_rating(ticker,overrides=None):
    s=get_snapshot(ticker);o=overrides or {}
    bank_anchor='a-';anchor=move(bank_anchor,-2) # a- -> bbb
    bp=o.get('BusinessProfile','Phù Hợp')
    ce=o.get('CapitalEarnings',_relative(s.get('ROE'),_industry_mean(ticker,'ROE')))
    rp=o.get('RiskPosition','Phù Hợp')
    fl=o.get('FundingLiquidity',_relative(s.get('CurrentRatio'),_industry_mean(ticker,'CurrentRatio')))
    factors={'Hồ sơ Kinh doanh':bp,'Vốn và Lợi nhuận':ce,'Vị thế Rủi ro':rp,'Nguồn vốn và Thanh khoản':fl}
    notches=sum(NOTCH.get(v,0) for v in factors.values())
    sacp=move(anchor,notches)
    # methodology floor, except default scenario
    if SCALE.index(sacp)>SCALE.index('b-') and not o.get('DefaultScenario',False):sacp='b-'
    if o.get('DefaultScenario',False):sacp='ccc'
    support=int(o.get('ExternalSupportNotches',0));icr=move(sacp,support)
    return {'Methodology':'SECURITIES','MethodologyName':'Phương pháp XHTN Công ty Chứng khoán','BICRAReference':label(bank_anchor),'SectorAnchorAdjustment':-2,'Anchor':label(anchor),'Factors':factors,'InternalNotches':notches,'SACP':label(sacp),'ExternalSupportNotches':support,'ICR':label(icr),'Audit':'BICRA tham chiếu → -2 bậc Anchor CTCK → 4 nhóm yếu tố nội sinh → SACP → hỗ trợ → ICR'}

def corporate_rating(ticker,overrides=None):
    o=overrides or {}; meta=get_company(ticker)
    # This engine follows the distinct corporate methodology. It does NOT reuse BICRA/notch logic.
    # Risk scores 1 (lowest) to 6 (highest). Auto values are deliberately provisional where qualitative KCF are absent.
    industry=float(o.get('IndustryRisk',3))
    business=float(o.get('BusinessRisk',3))
    financial=float(o.get('FinancialRisk',3))
    governance=float(o.get('GovernanceRisk',3))
    # Do not invent official sector weights. Equal-weight fallback is explicitly provisional unless analyst supplies weights.
    w=o.get('Weights',{'IndustryRisk':.25,'BusinessRisk':.25,'FinancialRisk':.25,'GovernanceRisk':.25})
    weighted=sum(v*w.get(k,0) for k,v in [('IndustryRisk',industry),('BusinessRisk',business),('FinancialRisk',financial),('GovernanceRisk',governance)])
    # Mapping is a transparent working implementation; analyst override is preserved for official committee use.
    if 'AnchorOverride' in o: anchor=str(o['AnchorOverride']).lower().replace('vn','')
    else:
        anchor='a' if weighted<=1.5 else 'bbb+' if weighted<=2.25 else 'bbb-' if weighted<=3 else 'bb+' if weighted<=3.75 else 'bb-' if weighted<=4.5 else 'b'
    modifier=int(o.get('ModifierNotches',0));sca=move(anchor,modifier)
    # Governance caps documented in methodology.
    if governance>=6 and SCALE.index(sca)<SCALE.index('b'):sca='b'
    elif governance>=5 and SCALE.index(sca)<SCALE.index('bb-'):sca='bb-'
    elif governance>=4 and SCALE.index(sca)<SCALE.index('bb+'):sca='bb+'
    liquidity=o.get('Liquidity','Trung Bình')
    if liquidity=='Yếu' and SCALE.index(sca)<SCALE.index('b'):sca='b'
    support=int(o.get('ExternalSupportNotches',0));icr=move(sca,support)
    return {'Methodology':'CORPORATE','MethodologyName':'Phương pháp XHTN Doanh nghiệp phi tài chính','RiskScores':{'Rủi ro Ngành':industry,'Rủi ro Kinh doanh':business,'Rủi ro Tài chính':financial,'Quản trị và Quản lý':governance},'Weights':w,'WeightedScore':weighted,'Anchor':label(anchor),'ModifierNotches':modifier,'SCA':label(sca),'ExternalSupportNotches':support,'ICR':label(icr),'ProvisionalAutoScoring':True,'Audit':'4 nhóm rủi ro (1–6) → tổng điểm có trọng số → Anchor → Modifiers → SCA → Support → ICR'}

def rate_company(ticker,overrides=None):
    m=get_company(ticker);typ=str(m.get('EntityType','CORPORATE'))
    method=str(m.get('Methodology',''))
    if method=='EXCLUDED_SPECIALIZED':
        return {'Methodology':'EXCLUDED_SPECIALIZED','MethodologyName':'Ngoài phạm vi phương pháp doanh nghiệp thông thường','ICR':'N/A','Audit':'Cần phương pháp chuyên biệt; không tự động XHTN.'}
    if typ=='BANK':return bank_rating(ticker,overrides)
    if typ=='SECURITIES':return securities_rating(ticker,overrides)
    return corporate_rating(ticker,overrides)
