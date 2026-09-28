import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np
from scripts.universal_data import get_company,get_snapshot,num
from scripts.multisector_valuation import valuation, latest_market_price
from scripts.valuation_regime import assess as valuation_regime

def _n(x,default=None):
    v=num(x)
    return default if v is None else v

def _med(vals):
    vals=[float(x) for x in vals if x is not None and np.isfinite(x) and x>0]
    return float(np.median(vals)) if vals else None

def fair_value_range(ticker, overrides=None):
    """Sector-aware Bear/Base/Bull scenario valuation.

    Bear/Base/Bull are produced from different operating + valuation assumptions,
    not a mechanical +/-20% band around Base.
    """
    o=overrides or {}
    s=get_snapshot(ticker)
    meta=get_company(ticker)
    typ=meta.get('EntityType')
    val=valuation(ticker,s)
    vr=valuation_regime(ticker)
    price=val.get('Price') or latest_market_price(ticker,s)

    base=_n(val.get('FairValue'))
    assumptions={}
    bear=bull=None

    if typ=='SECURITIES':
        eps=_n(val.get('DerivedEPS'), _n(s.get('EPS')))
        bvps=_n(val.get('DerivedBVPS'), _n(s.get('BVPS')))
        peer_pe=_n(val.get('PeerPE'))
        peer_pb=_n(val.get('PeerMultiple'))

        # CTCK: earnings are cyclical; book value is more stable.
        bear_eps=float(o.get('BearEPSFactor',0.80))
        bear_bv=float(o.get('BearBVPSFactor',0.97))
        bear_mult=float(o.get('BearMultipleFactor',0.85))
        bull_eps=float(o.get('BullEPSFactor',1.20))
        bull_bv=float(o.get('BullBVPSFactor',1.05))
        bull_mult=float(o.get('BullMultipleFactor',1.10))

        bear=_med([
            eps*bear_eps*peer_pe*bear_mult if eps and peer_pe else None,
            bvps*bear_bv*peer_pb*bear_mult if bvps and peer_pb else None
        ])
        bull=_med([
            eps*bull_eps*peer_pe*bull_mult if eps and peer_pe else None,
            bvps*bull_bv*peer_pb*bull_mult if bvps and peer_pb else None
        ])
        assumptions={
            'Bear':'EPS -20%; BVPS -3%; P/E và P/B peer chiết khấu 15%.',
            'Base':'P/E + P/B theo trung vị peer sau lọc outlier.',
            'Bull':'EPS +20%; BVPS +5%; P/E và P/B peer premium 10%.'
        }

    elif typ=='BANK':
        bvps=_n(val.get('DerivedBVPS'), _n(s.get('BVPS')))
        peer_pb=_n(val.get('PeerMultiple'))
        bear=_med([bvps*0.95*peer_pb*0.85 if bvps and peer_pb else None])
        bull=_med([bvps*1.08*peer_pb*1.10 if bvps and peer_pb else None])
        assumptions={
            'Bear':'BVPS -5%; P/B peer chiết khấu 15% do ROE/chất lượng tài sản yếu hơn.',
            'Base':'BVPS hiện tại × P/B trung vị peer.',
            'Bull':'BVPS +8%; P/B peer premium 10% khi ROE/chất lượng tài sản cải thiện.'
        }

    else:
        eps=_n(val.get('DerivedEPS'), _n(s.get('EPS')))
        peer_pe=_n(val.get('PeerMultiple'))
        bear=_med([eps*0.80*peer_pe*0.85 if eps and peer_pe else None])
        bull=_med([eps*1.20*peer_pe*1.10 if eps and peer_pe else None])
        assumptions={
            'Bear':'EPS -20%; P/E peer chiết khấu 15%.',
            'Base':'EPS hiện tại × P/E trung vị peer.',
            'Bull':'EPS +20%; P/E peer premium 10%.'
        }

    # Fallback only when a sector scenario cannot be calculated.
    if base is None:
        base=price
    if bear is None and base is not None:
        bear=base*0.80
        assumptions['Bear']=assumptions.get('Bear','Fallback: Base -20% do thiếu biến số kịch bản.')
    if bull is None and base is not None:
        bull=base*1.20
        assumptions['Bull']=assumptions.get('Bull','Fallback: Base +20% do thiếu biến số kịch bản.')

    control_premium=float(o.get('ControlPremium',0.15))
    strategic_synergy=float(o.get('StrategicSynergy',0.08))
    strategic=None if base is None else base*(1+control_premium+strategic_synergy)

    return {
        'Ticker':str(ticker).upper(),
        'CompanyName':meta.get('CompanyName'),
        'Sector':meta.get('Sector'),
        'EntityType':typ,
        'CurrentPrice':price,
        'Bear':bear,'Base':base,'Bull':bull,'StrategicMA':strategic,
        'ControlPremium':control_premium,'StrategicSynergy':strategic_synergy,
        'ValuationRegime':vr.get('Regime'),
        'ScenarioAssumptions':assumptions,
        'BaseSource':'Sector-specific peer valuation engine',
        'Warning':'Bear/Base/Bull là các kịch bản hoạt động + multiple; Strategic/M&A là kịch bản riêng và cần hiệu chỉnh theo giao dịch.'
    }
