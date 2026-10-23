"""Danh mục ICB dùng chung; đọc đúng schema long/wide của Vnstock Reference."""
from __future__ import annotations
from pathlib import Path
import re
import sys
import unicodedata
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CFG = ROOT / 'config'
ICB_COLUMNS = [f'ICB{kind}{lv}' for lv in range(1, 5) for kind in ('Code', 'Name')]


def _norm(value):
    s = unicodedata.normalize('NFKD', str(value).replace('đ', 'd').replace('Đ', 'D'))
    return re.sub(r'[^a-z0-9]+', '', s.encode('ascii', 'ignore').decode().lower())


def _first(df, names):
    # Không dùng substring: icb_code KHÔNG phải icb_code1/2/3/4.
    columns = {_norm(c): c for c in df.columns}
    return next((columns[_norm(n)] for n in names if _norm(n) in columns), None)


def clean(value):
    return '' if pd.isna(value) or str(value).strip().lower() in ('', 'nan', 'none', '<na>') else str(value).strip()


def code(value):
    return re.sub(r'\.0$', '', clean(value))


def normalize_industry_frames(frames, taxonomy=None):
    """Gộp theo ticker + cấp ICB, không làm mất các cấp khi nguồn có nhiều dòng/mã."""
    records = {}
    for df in frames:
        df = pd.DataFrame(df)
        tc = _first(df, ['Ticker', 'symbol'])
        if tc is None:
            continue
        lc, cc, nc = (_first(df, [x]) for x in ('icb_level', 'icb_code', 'icb_name'))
        wide = {(lv, kind): _first(df, [f'ICB{kind}{lv}', f'icb_{kind}_lv{lv}', f'icb_{kind}_{lv}', f'industry_{kind}_{lv}'])
                for lv in range(1, 5) for kind in ('Code', 'Name')}
        seen = {}
        for row in df.to_dict('records'):
            ticker = clean(row.get(tc)).upper()
            if not ticker:
                continue
            rec = records.setdefault(ticker, {'Ticker': ticker})
            values = {}
            if lc and cc:
                level = pd.to_numeric(row.get(lc), errors='coerce')
                if pd.notna(level) and level in (1, 2, 3, 4):
                    values[f'ICBCode{int(level)}'] = code(row.get(cc))
                    values[f'ICBName{int(level)}'] = clean(row.get(nc)) if nc else ''
            for (lv, kind), column in wide.items():
                if column:
                    values[f'ICB{kind}{lv}'] = code(row.get(column)) if kind == 'Code' else clean(row.get(column))
            for field, value in values.items():
                if not value:
                    continue
                key = (ticker, field)
                if field.startswith('ICBCode') and key in seen and seen[key] != value:
                    raise ValueError(f'ICB mâu thuẫn: {ticker} {field}: {seen[key]} / {value}')
                seen[key] = value
                # Nguồn chính đứng trước; nguồn bổ sung chỉ điền cấp còn thiếu.
                if not rec.get(field):
                    rec[field] = value
    out = pd.DataFrame(records.values()).reindex(columns=['Ticker', *ICB_COLUMNS]).fillna('')
    tax = pd.DataFrame(taxonomy) if taxonomy is not None else pd.DataFrame()
    if not tax.empty:
        cc, nc, lc = (_first(tax, [x]) for x in ('icb_code', 'icb_name', 'icb_level'))
        if cc and nc and lc:
            lookup = {(int(r[lc]), code(r[cc])): clean(r[nc]) for r in tax.to_dict('records')
                      if pd.to_numeric(r[lc], errors='coerce') in (1, 2, 3, 4)}
            for idx, row in out.iterrows():
                for lv in range(4, 0, -1):
                    current = code(out.at[idx, f'ICBCode{lv}'])
                    if not current:
                        continue
                    if not out.at[idx, f'ICBName{lv}']:
                        out.at[idx, f'ICBName{lv}'] = lookup.get((lv, current), '')
                    # Chỉ bổ sung tổ tiên ICB 4 chữ số có thật trong danh mục nguồn.
                    if re.fullmatch(r'\d{4}', current):
                        for parent in range(1, lv):
                            parent_code = current[:parent] + '0' * (4-parent)
                            if (parent, parent_code) in lookup and not out.at[idx, f'ICBCode{parent}']:
                                out.at[idx, f'ICBCode{parent}'] = parent_code
                                out.at[idx, f'ICBName{parent}'] = lookup[(parent, parent_code)]
    if out.empty or not out[[f'ICBCode{i}' for i in range(1, 5)]].ne('').any().any():
        raise ValueError('Nguồn Vnstock không có mã ICB theo cấp; giữ nguyên danh mục cũ.')
    return out.sort_values('Ticker').reset_index(drop=True)


def atomic_csv(frame, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    frame.to_csv(temp, index=False, encoding='utf-8-sig')
    temp.replace(path)


def fetch_industry_map():
    from scripts.vnstock_env import load_vnstock_env
    load_vnstock_env()
    from vnstock_data import Reference
    ref = Reference()
    # Hai lệnh cho toàn thị trường, không gọi company(ticker) trong báo cáo.
    sectors = pd.DataFrame(ref.industry.sectors(lang='vi'))
    taxonomy = pd.DataFrame(ref.industry.list(lang='vi'))
    listing = pd.read_csv(CFG/'vnstock_listing_full.csv', dtype=str) if (CFG/'vnstock_listing_full.csv').exists() else pd.DataFrame()
    result = normalize_industry_frames([sectors, listing], taxonomy)
    atomic_csv(sectors, CFG/'vnstock_industry_source.csv')
    atomic_csv(taxonomy, CFG/'vnstock_icb_taxonomy.csv')
    atomic_csv(result, CFG/'vnstock_industry_map.csv')
    return result


def _entity_and_method(*names):
    # Ngành chi tiết thắng tên công ty: công ty chứng khoán có chữ "Ngân hàng"
    # trong tên pháp lý vẫn phải đi theo phương pháp Securities.
    ordered = [*reversed(names[:-1]), names[-1]] if names else []
    for value in ordered:
        n = _norm(clean(value))
        if 'baohiem' in n or 'insurance' in n:
            return 'INSURANCE', 'INSURANCE_2025'
        if 'chungkhoan' in n or 'securities' in n or 'brokerage' in n:
            return 'SECURITIES', 'SECURITIES_2025'
        if 'nganhang' in n or 'bank' in n:
            return 'BANK', 'BANK_2026'
        if 'hangkhong' in n or 'airline' in n:
            return 'CORPORATE', 'EXCLUDED_SPECIALIZED'
    return 'CORPORATE', 'CORPORATE_2025'


def apply_industry_classification(industry_map=None):
    u = pd.read_csv(CFG/'company_universe.csv', dtype=str).fillna('')
    u['Ticker'] = u.Ticker.str.upper().str.strip()
    im = (industry_map.copy() if industry_map is not None else fetch_industry_map()).fillna('')
    im['Ticker'] = im.Ticker.astype(str).str.upper().str.strip()
    im = im.drop_duplicates('Ticker').set_index('Ticker')
    for c in ICB_COLUMNS + ['IndustryLevelUsed', 'IndustrySource']:
        if c not in u:
            u[c] = ''
    for idx, row in u.iterrows():
        t = row.Ticker
        if t not in im.index or not any(clean(im.loc[t].get(f'ICBCode{lv}')) for lv in range(1, 5)):
            continue  # Nguồn thiếu mã không được xóa metadata đã có.
        incoming = im.loc[t]
        for c in ICB_COLUMNS:
            u.at[idx, c] = clean(incoming.get(c))
        level = next(lv for lv in (4, 3, 2, 1) if clean(incoming.get(f'ICBCode{lv}')))
        sec = clean(incoming.get(f'ICBName{level}')) or f'ICB {incoming[f"ICBCode{level}"]}'
        et, method = _entity_and_method(*(incoming.get(f'ICBName{lv}') for lv in range(1, 5)), row.get('CompanyName'))
        u.loc[idx, ['Sector', 'EntityType', 'Methodology', 'PeerGroup', 'IndustryLevelUsed', 'IndustrySource']] = [sec, et, method, sec, f'ICBCode{level}', 'VNSTOCK_ICB_AUTO_V8.123']
    registry_path = CFG/'insurance_entities.csv'
    if registry_path.exists():
        registry = pd.read_csv(registry_path)
        mask = u.Ticker.isin(registry.Ticker.astype(str).str.upper())
        u.loc[mask, ['EntityType', 'Methodology', 'Sector', 'PeerGroup']] = ['INSURANCE', 'INSURANCE_2025', 'Bảo hiểm', 'Bảo hiểm']
    atomic_csv(u, CFG/'company_universe.csv')
    audit = u.groupby(['EntityType', 'Sector'], dropna=False).size().reset_index(name='Companies')
    atomic_csv(audit, CFG/'industry_classification_audit.csv')
    print(f'OK - cập nhật ICB dùng chung cho {len(u)} mã; giữ metadata cũ khi nguồn thiếu mã.')
    return u


if __name__ == '__main__':
    apply_industry_classification()
