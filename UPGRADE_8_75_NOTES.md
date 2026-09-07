# V8.75 - Bank & Securities Analytical Rating Report

Changed files:
- app.py
- scripts/multisector_report.py

Main upgrades:
1. BANK rating report: deeper KPI analysis of franchise/scale, profitability, capital, asset quality, funding and liquidity.
2. SECURITIES rating report: deeper analysis of capital adequacy, leverage, profitability, margin/balance-sheet risk, funding and liquidity.
3. Methodology text remains compact; factual KPI/peer analysis is prioritized.
4. Final section of EVERY rating report is now "TỔNG KẾT CẤU PHẦN XẾP HẠNG".
   - BANK/SECURITIES: starting point/anchor -> factor assessment -> +/- notch -> SACP -> support -> ICR.
   - CORPORATE: 1-6 component scores -> liquidity/modifiers -> SCA -> support -> ICR.
5. App rating tab also shows the same final component/notch bridge.

No Full Refresh required. Copy the changed files, run locally, export KLB and VDS reports, then push after visual review.
