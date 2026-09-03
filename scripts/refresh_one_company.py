from pathlib import Path
import subprocess, sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / 'config' / 'company_universe.csv'

def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/refresh_one_company.py <TICKER>')
        raise SystemExit(2)
    ticker = sys.argv[1].strip().upper()
    if not CFG.exists():
        print('Không tìm thấy config/company_universe.csv')
        raise SystemExit(2)
    u = pd.read_csv(CFG)
    u['Ticker'] = u['Ticker'].astype(str).str.upper().str.strip()
    z = u[u['Ticker'].eq(ticker)]
    if z.empty:
        print(f'Không tìm thấy {ticker} trong company_universe.csv')
        raise SystemExit(2)
    etype = str(z.iloc[0].get('EntityType','')).upper().strip()
    py = sys.executable
    if etype == 'BANK':
        cmd = [py, str(ROOT/'scripts'/'refresh_vnstock.py'), '--tickers', ticker]
    else:
        cmd = [py, str(ROOT/'scripts'/'refresh_vnstock_multisector.py'), ticker]
    print(f'Routing {ticker}: EntityType={etype} -> {Path(cmd[1]).name}')
    rc = subprocess.call(cmd, cwd=str(ROOT))
    raise SystemExit(rc)

if __name__ == '__main__':
    main()
