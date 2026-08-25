from pathlib import Path
import py_compile, pandas as pd
ROOT=Path(__file__).resolve().parents[1]
for f in [ROOT/'app.py',ROOT/'scripts/universal_data.py',ROOT/'scripts/multisector_rating.py',ROOT/'scripts/multisector_valuation.py',ROOT/'scripts/multisector_report.py',ROOT/'scripts/refresh_vnstock_multisector.py']:
    py_compile.compile(str(f),doraise=True)
u=pd.read_csv(ROOT/'config/company_universe.csv')
assert {'BANK','SECURITIES','CORPORATE'}.issubset(set(u.EntityType))
assert len(u)>=60
r=pd.read_csv(ROOT/'config/corporate_rating_scale.csv'); assert len(r)>=17
m=pd.read_csv(ROOT/'config/methodology_router.csv'); assert len(m)>=4
print(f'OK - V8 validation passed: {len(u)} seed tickers; 3 entity engines; methodology eligibility gate active.')
