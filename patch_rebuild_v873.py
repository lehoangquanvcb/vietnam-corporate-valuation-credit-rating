from pathlib import Path

p = Path("scripts/rebuild_multisector_from_raw.py")

new = r'''from __future__ import annotations

from pathlib import Path
from datetime import datetime
import argparse
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
CFG = ROOT / "config"
FUND_PARTS = DATA / "fundamentals_long"
FUND_PARTS.mkdir(parents=True, exist_ok=True)

# Reuse the production V8.73 parser. Importing this module does not call fetch().
sys.path.insert(0, str(ROOT / "scripts"))
import refresh_vnstock_multisector as parser

PARSER_VERSION = "8.73.0"
SOURCE_MODE = "VNSTOCK_RAW_RECOVERY_V873"


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_raw(ticker, kind):
    p = RAW / f"{ticker}_{kind}.csv"
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()


def core_usable(row):
    if not isinstance(row, dict):
        return False

    rev = pd.to_numeric(row.get("Revenue"), errors="coerce")
    npat = pd.to_numeric(row.get("NPAT"), errors="coerce")
    assets = pd.to_numeric(row.get("TotalAssets"), errors="coerce")
    equity = pd.to_numeric(row.get("Equity"), errors="coerce")

    if not np.isfinite(rev) or rev <= 0:
        return False
    if not np.isfinite(assets) or assets <= 0:
        return False
    if not np.isfinite(npat):
        return False
    if not np.isfinite(equity):
        return False

    if str(row.get("Revenue_Basis", "")) != "TTM4Q":
        return False
    if str(row.get("NPAT_Basis", "")) != "TTM4Q":
        return False

    return True


def source_for_metric(metric, ratio, bs, inc, cf):
    if metric in parser.RATIO_METRICS:
        return ratio
    if metric in parser.STOCK_METRICS:
        return bs
    if metric in {"CFO", "Capex", "Depreciation"}:
        return cf
    return inc


def build_ticker(ticker):
    ratio = read_raw(ticker, "ratio")
    bs = read_raw(ticker, "balance")
    inc = read_raw(ticker, "income")
    cf = read_raw(ticker, "cashflow")

    if all(x.empty for x in (ratio, bs, inc, cf)):
        return None, [], None, "NO_RAW"

    row = {
        "Ticker": ticker,
        "RetrievedAt": now(),
        "DataType": "ACTUAL",
        "SourceMode": SOURCE_MODE,
        "ParserVersion": PARSER_VERSION,
        "VnstockDataVersion": getattr(parser, "VNSTOCK_DATA_VERSION", ""),
        "ParserLog": "OFFLINE_RECOVERED_FROM_RAW_V873",
        "SnapshotPeriod": "LATEST_QUARTER",
        "FlowBasis": "TTM_LAST_4_CONSECUTIVE_QUARTERS_STRICT",
    }

    hist = []

    for metric, names in parser.MAP.items():
        source = source_for_metric(metric, ratio, bs, inc, cf)

        try:
            if metric in parser.SEMANTIC_IDS:
                value, meta = parser._exact_semantic_snapshot(
                    source,
                    parser.SEMANTIC_IDS[metric],
                    parser._metric_kind(metric),
                    True,
                )
            else:
                value, meta = parser.metric_snapshot(
                    source,
                    names,
                    parser._metric_kind(metric),
                    True,
                )
        except Exception as e:
            value = np.nan
            meta = {
                "row": "",
                "basis": "PARSER_ERROR",
                "periods": [],
            }
            row["ParserLog"] += f" | {metric}:{type(e).__name__}:{e}"

        row[metric] = (
            parser.normalize_metric_value(metric, value)
            if pd.notna(value)
            else np.nan
        )

        row[f"{metric}_SourceRow"] = meta.get("row", "")
        row[f"{metric}_Basis"] = meta.get("basis", "")
        row[f"{metric}_Periods"] = "|".join(meta.get("periods", []) or [])

        try:
            if metric in parser.SEMANTIC_IDS:
                hist += parser._exact_semantic_history(
                    source,
                    ticker,
                    metric,
                    parser.SEMANTIC_IDS[metric],
                )
            else:
                hist += parser.hist_rows_any(
                    source,
                    ticker,
                    metric,
                    names,
                )
        except Exception as e:
            row["ParserLog"] += f" | HIST_{metric}:{type(e).__name__}:{e}"

    # Deterministic interest-bearing debt, consistent with online V8.73.
    debt_parts = []
    debt_meta = []

    for _, semantic_ids in parser.BORROWING_SEMANTIC_IDS.items():
        try:
            value, meta = parser._exact_semantic_snapshot(
                bs, semantic_ids, "stock", True
            )
            if pd.notna(value):
                debt_parts.append(float(value))
                debt_meta.append(meta)
        except Exception:
            pass

    if len(debt_parts) == 2:
        row["TotalDebt"] = float(sum(debt_parts))
        row["TotalDebt_SourceRow"] = (
            "BS_SHORT_TERM_BORROWINGS+BS_LONG_TERM_BORROWINGS"
        )
        row["TotalDebt_Basis"] = "DERIVED_LATEST_Q"
        row["TotalDebt_Periods"] = "|".join(
            sorted(
                set(
                    period
                    for meta in debt_meta
                    for period in meta.get("periods", [])
                )
            )
        )

    parts = []

    for dataset, df in (
        ("ratio", ratio),
        ("balance_sheet", bs),
        ("income_statement", inc),
        ("cash_flow", cf),
    ):
        if df.empty:
            continue
        try:
            z = parser.generic_long(df, ticker, dataset)
            if isinstance(z, list):
                z = pd.DataFrame(z)
            if z is not None and len(z):
                parts.append(z)
        except Exception as e:
            row["ParserLog"] += f" | LONG_{dataset}:{type(e).__name__}:{e}"

    long_df = (
        pd.concat(parts, ignore_index=True)
        if parts
        else pd.DataFrame()
    )

    return row, hist, long_df, "OK" if core_usable(row) else "INCOMPLETE"


def main():
    ap = argparse.ArgumentParser(
        description="V8.73 offline multisector rebuild from existing raw files"
    )
    ap.add_argument(
        "--tickers",
        default="",
        help="Comma-separated ticker subset. Empty means all active non-banks.",
    )
    ap.add_argument("--compact", action="store_true")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate only; do not write output files.",
    )
    args = ap.parse_args()

    universe = pd.read_csv(CFG / "company_universe.csv")
    universe["Ticker"] = (
        universe["Ticker"].astype(str).str.upper().str.strip()
    )

    if "Active" in universe.columns:
        universe = universe[
            pd.to_numeric(
                universe["Active"], errors="coerce"
            ).fillna(1).eq(1)
        ]

    universe = universe[
        ~universe["EntityType"].astype(str).str.upper().eq("BANK")
    ]

    if args.tickers.strip():
        wanted = {
            x.strip().upper()
            for x in args.tickers.split(",")
            if x.strip()
        }
        universe = universe[universe["Ticker"].isin(wanted)]

    tickers = universe["Ticker"].dropna().unique().tolist()

    old = (
        pd.read_csv(DATA / "company_snapshot.csv")
        if (DATA / "company_snapshot.csv").exists()
        else pd.DataFrame()
    )

    accepted = []
    hist = []
    manifest = []
    compact = []
    incomplete = []

    for i, ticker in enumerate(tickers, 1):
        row, h, long_df, status = build_ticker(ticker)

        if row is None:
            print(f"[{i}/{len(tickers)}] {ticker}: NO_RAW")
            incomplete.append(ticker)
            continue

        print(
            f"[{i}/{len(tickers)}] {ticker}: {status}"
            f" | Revenue={row.get('Revenue')}"
            f" | NPAT={row.get('NPAT')}"
            f" | Assets={row.get('TotalAssets')}"
            f" | Equity={row.get('Equity')}"
            f" | Basis={row.get('Revenue_Basis')}/{row.get('NPAT_Basis')}"
            f" | Periods={row.get('Revenue_Periods')}"
        )

        # Critical guard: incomplete recovery NEVER replaces a snapshot.
        if status != "OK":
            incomplete.append(ticker)
            continue

        accepted.append(row)
        hist += h

        if long_df is not None and len(long_df):
            if not args.dry_run:
                fp = FUND_PARTS / f"{ticker}.csv"
                long_df.to_csv(
                    fp,
                    index=False,
                    encoding="utf-8-sig",
                )
                manifest.append(
                    {
                        "Ticker": ticker,
                        "Rows": len(long_df),
                        "Path": str(
                            fp.relative_to(ROOT)
                        ).replace("\\", "/"),
                        "RetrievedAt": now(),
                    }
                )

            if args.compact:
                compact.append(long_df)

    if args.dry_run:
        print(
            f"DRY RUN DONE | valid={len(accepted)}"
            f" | incomplete={len(incomplete)}"
            f" | total={len(tickers)}"
        )
        return

    new = pd.DataFrame(accepted)

    if len(new):
        if len(old) and "Ticker" in old.columns:
            old = old[
                ~old["Ticker"]
                .astype(str)
                .str.upper()
                .isin(new["Ticker"].astype(str).str.upper())
            ]

        pd.concat(
            [old, new],
            ignore_index=True,
        ).sort_values("Ticker").drop_duplicates(
            "Ticker", keep="last"
        ).to_csv(
            DATA / "company_snapshot.csv",
            index=False,
            encoding="utf-8-sig",
        )

    oldh = (
        pd.read_csv(DATA / "company_history_long.csv")
        if (DATA / "company_history_long.csv").exists()
        else pd.DataFrame()
    )
    nh = pd.DataFrame(hist)

    if len(nh):
        ah = (
            pd.concat([oldh, nh], ignore_index=True)
            if len(oldh)
            else nh
        )
        ah.drop_duplicates(
            ["Ticker", "Period", "Metric"],
            keep="last",
        ).to_csv(
            DATA / "company_history_long.csv",
            index=False,
            encoding="utf-8-sig",
        )

    if manifest:
        pd.DataFrame(manifest).sort_values(
            "Ticker"
        ).to_csv(
            DATA / "vnstock_company_fundamentals_manifest.csv",
            index=False,
            encoding="utf-8-sig",
        )

    if args.compact and compact:
        pd.concat(
            compact,
            ignore_index=True,
        ).to_csv(
            DATA / "vnstock_company_fundamentals_long.csv",
            index=False,
            encoding="utf-8-sig",
        )

    print(
        f"DONE V8.73 OFFLINE RECOVERY"
        f" | accepted={len(accepted)}"
        f" | incomplete={len(incomplete)}"
        f" | total={len(tickers)}"
    )

    if incomplete:
        print(
            "INCOMPLETE_FIRST_30="
            + ",".join(incomplete[:30])
        )


if __name__ == "__main__":
    main()
'''

p.write_text(new, encoding="utf-8")
print("PATCHED:", p)