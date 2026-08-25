import numpy as np
import pandas as pd


def _compat(self):
    out=[]
    for item in self.tolist():
        vals=item if isinstance(item,tuple) else (item,)
        out.append(any(bool(pd.isna(v)) for v in vals))
    return np.asarray(out,dtype=bool)

mi=pd.MultiIndex.from_tuples([('A',1),(None,2)])
# Method-level compatibility used by refresh_vnstock.
try:
    mi.isna()
except NotImplementedError:
    pd.MultiIndex.isna=_compat
assert mi.isna().tolist()==[False,True]

# Top-level pandas.isna(MultiIndex) is the actual failure path seen in
# vnstock_data on recent pandas builds. Mirror the production guard.
_native=pd.isna
def _top(obj):
    if isinstance(obj,pd.MultiIndex):
        return _compat(obj)
    return _native(obj)
pd.isna=_top
pd.isnull=_top
assert pd.isna(mi).tolist()==[False,True]
print('OK - pandas MultiIndex method + top-level isna compatibility guards work.')
