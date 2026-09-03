import sys, importlib, traceback, os
from vnstock_env import load_vnstock_env

status = load_vnstock_env()
print('Python:', sys.executable)
print('Version:', sys.version.replace('\n',' '))
print('.env:', 'FOUND' if status['env_file_exists'] else 'NOT FOUND', '|', status['env_file'])
print('VNSTOCK_API_KEY:', status['api_key_masked'])
print('VNSTOCK_VENV_PATH:', status['venv_path'] or os.getenv('VNSTOCK_VENV_PATH') or 'NOT SET')
print('VNSTOCK_INTERACTIVE:', os.getenv('VNSTOCK_INTERACTIVE',''))

vnstock_data_ok = False
for mod in ['vnstock_data','vnstock']:
    try:
        m=importlib.import_module(mod)
        print(f'{mod}: OK | file={getattr(m,"__file__",None)} | version={getattr(m,"__version__","N/A")}')
        if mod=='vnstock_data':
            vnstock_data_ok = True
            for name in ['Reference','Fundamental','Market','Quote','Insights','Macro']:
                print(f'  {name}:', 'YES' if hasattr(m,name) else 'NO')
    except Exception as e:
        print(f'{mod}: NOT AVAILABLE | {type(e).__name__}: {e}')

print('\nSponsor access smoke test:')
if not vnstock_data_ok:
    print('ERROR - vnstock_data is not installed in the selected Python environment.')
    sys.exit(2)

try:
    from vnstock_data import Reference
    ref=Reference(); df=ref.equity.list()
    print('Sponsor authentication: OK (vnstock_data request succeeded)')
    if not status['api_key_present']:
        print('Credential source: existing Vnstock local authentication/profile (VNSTOCK_API_KEY env var not required for this machine)')
    else:
        print('Credential source: VNSTOCK_API_KEY environment/.env')
    print('Reference().equity.list(): OK | rows=',len(df),'| columns=',list(df.columns)[:30])
except Exception:
    print('ERROR - vnstock_data imported, but Sponsor request failed:')
    traceback.print_exc()
    sys.exit(3)
