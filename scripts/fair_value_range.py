import sys as _sys
from pathlib import Path as _Path
_PROJECT_ROOT = _Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.universal_data import get_company,get_snapshot,num
from scripts.multisector_valuation import valuation
from scripts.valuation_regime import assess as valuation_regime

def _n(x,default=None):
    v=num(x)
    return default if v is None else v

def fair_value_range(ticker, overrides=None):
    """
    Bear/Base/Bull + Strategic/M&A value.
    Uses existing valuation engine as the base source and NEVER hard-codes STB-specific
    80k-100k assumptions into other issuers.
    """
    o=overrides or {}
    s=get_snapshot(ticker)
    meta=get_company(ticker)
    val=valuation(ticker,s)
    vr=valuation_regime(ticker)

    price=_n(s.get('Price'), _n(s.get('Close')))
    # Reuse whatever fair-value field the inherited engine already produces.
    candidates=['FairValue','TargetPrice','BaseValue','IntrinsicValue','EquityValuePerShare','ValuePerShare']
    base=None
    for k in candidates:
        base=_n(val.get(k))
        if base is not None: break
    if base is None:
        # transparent fallback: current price as neutral reference, not an asserted fair value
        base=price

    bear_haircut=float(o.get('BearHaircut',0.20))
    bull_premium=float(o.get('BullPremium',0.20))
    control_premium=float(o.get('ControlPremium',0.25))
    strategic_synergy=float(o.get('StrategicSynergy',0.10))

    bear=None if base is None else base*(1-bear_haircut)
    bull=None if base is None else base*(1+bull_premium)
    strategic=None if base is None else base*(1+control_premium+strategic_synergy)

    return {
        'Ticker':str(ticker).upper(),
        'CompanyName':meta.get('CompanyName'),
        'Sector':meta.get('Sector'),
        'CurrentPrice':price,
        'Bear':bear,'Base':base,'Bull':bull,'StrategicMA':strategic,
        'BearHaircut':bear_haircut,'BullPremium':bull_premium,
        'ControlPremium':control_premium,'StrategicSynergy':strategic_synergy,
        'ValuationRegime':vr.get('Regime'),
        'BaseSource':'Inherited valuation engine' if any(_n(val.get(k)) is not None for k in candidates) else 'Current-price neutral reference because inherited fair value is unavailable',
        'Warning':'Strategic/M&A value is scenario analysis, not a universal control-premium rule. Analyst must override assumptions for the specific transaction.'
    }
