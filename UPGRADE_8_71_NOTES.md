# V8.71 - Bronze Rate-Limit Safe Full Refresh

- 1 worker for full refresh.
- 2.5 second delay between ticker batches.
- Preserves V8.70 strict semantic-period and leverage/cash-flow parser.
- Local Bronze -> ACTUAL CSV -> GitHub -> Streamlit unchanged.
