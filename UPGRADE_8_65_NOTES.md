# 8.65 Quick one-company rebuild

- RUN_REFRESH_ONE_AND_REBUILD no longer recalculates Intelligent Analyst for all ~1,751 tickers.
- Dynamic peer and sector benchmark accept a ticker and upsert only that ticker.
- Intelligent analyst accepts a ticker and upserts only that ticker.
- Valuation peer median drops NaN values before median calculation to prevent `Mean of empty slice` warning floods.
- Full-market scripts still support ALL mode for scheduled/full refreshes.
