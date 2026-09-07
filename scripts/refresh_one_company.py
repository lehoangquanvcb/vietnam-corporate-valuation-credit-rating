from pathlib import Path
import subprocess, sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / 'config' / 'company_universe.csv'

def main():
    print('REFRESH ONE ENGINE v8.70 STRICT LEVERAGE/CASH-FLOW MODE')
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
    if rc != 0:
        raise SystemExit(rc)
    # 8.68: verify THIS run succeeded; never validate a stale snapshot from an earlier run.
    if etype != 'BANK':
        logp=ROOT/'data'/'refresh_log_multisector.csv'
        if not logp.exists():
            print('FAILED CURRENT REFRESH - refresh log missing')
            raise SystemExit(7)
        lg=pd.read_csv(logp)
        cur=lg[lg.get('Dataset',pd.Series(dtype=str)).astype(str).eq(f'company:{ticker}')]
        if cur.empty or str(cur.iloc[-1].get('Status','')).upper()!='OK':
            msg='' if cur.empty else str(cur.iloc[-1].get('Message',''))
            print('FAILED CURRENT REFRESH - parser/fetch did not complete:', msg)
            print(f'Run: {py} scripts/diagnose_vnstock.py {ticker}')
            raise SystemExit(7)

    # Hard gate for non-bank refreshes: never report success when the parser
    # produced an empty corporate snapshot.
    if etype != 'BANK':
        snap = ROOT / 'data' / 'company_snapshot.csv'
        if not snap.exists():
            print('FAILED FUNDAMENTAL PARSING - company_snapshot.csv was not created')
            raise SystemExit(5)
        d = pd.read_csv(snap)
        d['Ticker'] = d['Ticker'].astype(str).str.upper().str.strip()
        z2 = d[d['Ticker'].eq(ticker)]
        required=['Revenue','TotalAssets','Equity','NPAT']
        missing=[]
        if z2.empty:
            missing=required
        else:
            r=z2.iloc[-1]
            for k in required:
                if k not in z2.columns or pd.isna(pd.to_numeric(pd.Series([r.get(k)]),errors='coerce').iloc[0]): missing.append(k)
        # Revenue/NPAT must be true TTM4Q; stale/FY/single-quarter values are rejected.
        if not z2.empty:
            rr=z2.iloc[-1]
            for k in ['Revenue','NPAT']:
                if str(rr.get(k+'_Basis','')).upper() not in {'TTM4Q','TTM4Q_COLUMN'} and k not in missing:
                    missing.append(k+'[TTM4Q_REQUIRED]')
        if missing:
            print('FAILED FUNDAMENTAL PARSING - missing/invalid required KPIs:', ', '.join(missing))
            print(f'Run: {py} scripts/diagnose_vnstock.py {ticker}')
            raise SystemExit(6)
        print('FUNDAMENTAL PARSING GATE: PASSED | Revenue + TotalAssets + Equity + NPAT available')
        vals={k:pd.to_numeric(pd.Series([z2.iloc[-1].get(k)]),errors='coerce').iloc[0] for k in required}
        print('PARSED KPIs:', vals)
        extra={}
        for k in ['PE','PB','ROE','ROA','DebtEquity','DebtEBITDA','CurrentRatio','CFO_Debt','FOCF_Debt','CashDebt']:
            if k in z2.columns:
                v=pd.to_numeric(pd.Series([z2.iloc[-1].get(k)]),errors='coerce').iloc[0]
                if pd.notna(v): extra[k]=float(v)
        print('PARSED RATIOS/DERIVED:', extra)
        print('PERIOD POLICY: exact semantic ID; stock/ratio=latest quarter; flow=TTM latest 4 consecutive quarters STRICT')
        audit={}
        for k in ['Revenue','NPAT','TotalAssets','Equity','PE','PB','TotalDebt','OperatingProfit','Depreciation','EBITDA','CFO','Capex']:
            audit[k]={'row':r.get(k+'_SourceRow',''),'basis':r.get(k+'_Basis',''),'periods':r.get(k+'_Periods','')}
        print('PERIOD/SEMANTIC AUDIT:', audit)
        # Strict sanity warnings: do not silently accept obviously broken parsing.
        rev=pd.to_numeric(pd.Series([r.get('Revenue')]),errors='coerce').iloc[0]
        pe=pd.to_numeric(pd.Series([r.get('PE')]),errors='coerce').iloc[0]
        pb=pd.to_numeric(pd.Series([r.get('PB')]),errors='coerce').iloc[0]
        if pd.notna(rev) and str(r.get('Revenue_Basis','')).upper()=='TTM4Q':
            print('TTM REVENUE CHECK: OK |', rev)
        else:
            print('WARNING - Revenue did not use TTM4Q; basis=',r.get('Revenue_Basis'))
        if pd.isna(pe) or pd.isna(pb):
            print('WARNING - PE/PB not parsed from latest ratio period; run diagnose_vnstock.py if raw ratio has values.')
        if etype == 'CORPORATE':
            de=pd.to_numeric(pd.Series([r.get('DebtEBITDA')]),errors='coerce').iloc[0]
            cfd=pd.to_numeric(pd.Series([r.get('CFO_Debt')]),errors='coerce').iloc[0]
            if pd.notna(de): print('LEVERAGE CHECK: Debt/EBITDA =', float(de),'x | basis=',r.get('DebtEBITDA_Basis',''))
            else: print('WARNING - Debt/EBITDA unavailable after strict derivation.')
            if pd.notna(cfd): print('CASH-FLOW CHECK: CFO/Debt =', float(cfd),'| basis=',r.get('CFO_Debt_Basis',''))
            else: print('WARNING - CFO/Debt unavailable after strict derivation.')
    raise SystemExit(0)

if __name__ == '__main__':
    main()
