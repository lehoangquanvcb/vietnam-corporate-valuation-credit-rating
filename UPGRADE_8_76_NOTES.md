# V8.76 — Rating Report Analysis + Peer Bar + Final Scorecard Fix

Changed file:
- scripts/multisector_report.py

What is fixed:
1. The report is analysis-led. Methodology exposition is not repeated in the body.
2. Every key chart shown in analytical sections is now a PAIR:
   - left: 2-line history = Company + peer mean;
   - right: bar chart at the Company's latest reporting period = Company + up to 10 peers.
3. The bar chart is period-aligned. If the Company's latest metric is 2026-Q2, peer values are also taken from 2026-Q2; different reporting periods are not mixed silently.
4. Analytical blocks show up to 2 key KPI chart pairs, plus narrative and a compact KPI/peer table.
5. Fixed V8.75 scorecard placement bug.
6. The rating component/notch scorecard is now literally the FINAL section of the rating report.
   - BANK/SECURITIES: starting point -> factor score -> +/- notch -> SACP -> external support -> ICR.
   - CORPORATE: component scores -> liquidity/modifier -> SCA -> support -> ICR.
7. No Full Refresh required.

Recommended test:
- Export KLB rating report and VDS rating report locally.
- Confirm ROE/NIM/NPL/CAR/CASA/LDR (bank) and ROE/capital adequacy/leverage/current ratio (securities) each have paired line+bar views where data exists.
- Confirm the last report section is TỔNG KẾT CẤU PHẦN XẾP HẠNG.
