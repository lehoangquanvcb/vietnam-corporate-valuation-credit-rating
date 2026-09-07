# 8.62 - Corporate Rating & Vnstock v3.2.8 Fundamental Fix

## Root cause fixed
Vnstock Data v3.2.8 changed Fundamental outputs to tidy/long by default. The old parser searched KPI names in DataFrame columns, so corporate financials could be downloaded successfully but normalized snapshot fields became N/A. The refresh engine now explicitly requests `format="time_series"`, uses VAS Semantic IDs/aliases, and forces `com_type="regular"` or `"securities"`.

## Corporate rating methodology
- No longer assigns 3/6 to all four corporate risk groups by default.
- No longer outputs vnBBB- when company/peer evidence is insufficient.
- Business risk uses scale, operating efficiency, profitability and peer evidence.
- Financial risk uses leverage, net leverage, CFO/FOCF debt coverage and liquidity metrics.
- Governance remains qualitative/neutral unless analyst evidence or override exists.
- Liquidity is a separate modifier/cap, consistent with the sample corporate report structure.
- Dynamic peer remains ICB/sector-first and now has a metadata fallback while financial data are incomplete.

## Corporate report order
Drivers -> Outlook -> Issuer overview -> Macro risk -> Industry risk -> Business risk -> Financial risk -> Governance & management -> Liquidity -> External support -> Rating sensitivity.

## Recommended first run
Run `RUN_REFRESH_ONE_AND_REBUILD.bat`, input `HPG`, verify HPG has actual Revenue/Assets/ROE/Leverage/CFO and peers. Then run `RUN_FULL_REFRESH.bat` for the full market after confirming the single-company result.
