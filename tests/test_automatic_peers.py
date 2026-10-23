"""Hồi quy ICB, peer toàn thị trường và cache không phụ thuộc prepare từng mã."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest
import pandas as pd
from scripts import industry_classifier as icb
from scripts import dynamic_peer_engine as engine
from scripts import refresh_market_peers as refresh


def metadata():
    return pd.DataFrame([
        dict(Ticker=t, EntityType='CORPORATE', CompanyName=t, Sector='Công nghiệp',
             ICBCode4=leaf, ICBCode3='2300', ICBCode2='2000', Active=active)
        for t,leaf,active in [('AAA','2353',1),('BBB','2353',1),('CCC','2357',1),('OFF','2353',0)]])


def snap(t, period='2026-Q2', basis='END_PERIOD', value=100):
    return {'Ticker':t, 'TotalAssets':value, '_MetricEvidence':{
        'TotalAssets':{'Metric':'TotalAssets','Value':value,'Status':'OK','Period':period,'Basis':basis,'Source':'fixture','Reason':''}}}


class IndustryTests(unittest.TestCase):
    def test_zero_prefixed_icb_survives_csv_reader_used_by_reports(self):
        from scripts.universal_data import read_csv
        with TemporaryDirectory() as folder:
            path=Path(folder)/'company_universe.csv'
            path.write_text('Ticker,ICBCode4,Active\nAAA,0533,1\n')
            row=read_csv(path).iloc[0]
            self.assertEqual(row.ICBCode4,'0533')

    def test_specialized_industry_wins_over_bank_word_in_company_name(self):
        self.assertEqual(icb._entity_and_method('Tài chính','','','Môi giới chứng khoán','Công ty chứng khoán Ngân hàng Đầu tư')[0],'SECURITIES')
        self.assertEqual(icb._entity_and_method('Tài chính','','','Bảo hiểm phi nhân thọ','ABC')[0],'INSURANCE')

    def test_long_schema_preserves_all_levels(self):
        source = pd.DataFrame([{'symbol':'AAA','icb_level':lv,'icb_code':c,'icb_name':n} for lv,c,n in
            [(1,'0001','N1'),(2,'0100','N2'),(3,'0130','N3'),(4,'0135','N4')]])
        row = icb.normalize_industry_frames([source]).iloc[0]
        self.assertEqual([row[f'ICBCode{i}'] for i in range(1,5)], ['0001','0100','0130','0135'])

    def test_wide_and_long_complement_each_other(self):
        a = pd.DataFrame([dict(symbol='AAA',icb_level=4,icb_code='2353',icb_name='Thép')])
        b = pd.DataFrame([dict(symbol='AAA',icb_code_lv2=2300)])
        row = icb.normalize_industry_frames([a,b]).iloc[0]
        self.assertEqual(row.ICBCode4, '2353')
        self.assertEqual(row.ICBCode2, '2300')
        self.assertEqual(row.ICBCode1, '')

    def test_generic_code_without_level_is_not_four_levels(self):
        with self.assertRaises(ValueError):
            icb.normalize_industry_frames([pd.DataFrame([dict(symbol='AAA',icb_code='2353',icb_name='Thép')])])

    def test_duplicate_conflicting_level_fails(self):
        source = pd.DataFrame([dict(symbol='AAA',icb_level=4,icb_code=c) for c in ['2353','2357']])
        with self.assertRaisesRegex(ValueError, 'ICB mâu thuẫn'):
            icb.normalize_industry_frames([source])

    def test_taxonomy_supplies_only_known_ancestors(self):
        source = pd.DataFrame([dict(symbol='AAA',icb_level=4,icb_code='2353',icb_name='Thép')])
        tax = pd.DataFrame([dict(icb_level=lv,icb_code=c,icb_name=f'N{lv}') for lv,c in [(1,'2000'),(2,'2300'),(3,'2350')]])
        row = icb.normalize_industry_frames([source], tax).iloc[0]
        self.assertEqual([row[f'ICBCode{i}'] for i in range(1,5)], ['2000','2300','2350','2353'])

    def test_partial_update_preserves_missing_ticker(self):
        with TemporaryDirectory() as folder, patch.object(icb, 'CFG', Path(folder)):
            u = metadata().assign(Methodology='CORPORATE_2025', PeerGroup='Công nghiệp')
            u.to_csv(Path(folder)/'company_universe.csv', index=False)
            new = pd.DataFrame([dict(Ticker='AAA',ICBCode4='9537',ICBName4='Phần mềm')])
            out = icb.apply_industry_classification(new).set_index('Ticker')
            self.assertEqual(out.loc['BBB','ICBCode4'], '2353')
            self.assertEqual(out.loc['AAA','Sector'], 'Phần mềm')

    def test_provider_called_once_for_whole_market(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        source = pd.DataFrame([dict(symbol=t,icb_level=4,icb_code='2353') for t in ['AAA','BBB']])
        provider = Mock()
        provider.industry.sectors.return_value = source
        provider.industry.list.return_value = pd.DataFrame()
        with TemporaryDirectory() as folder, patch.object(icb,'CFG',Path(folder)), patch.dict('sys.modules',{
            'vnstock_data':SimpleNamespace(Reference=lambda:provider),
            'scripts.vnstock_env':SimpleNamespace(load_vnstock_env=lambda:None)}):
            result = icb.fetch_industry_map()
        self.assertEqual(len(result), 2)
        provider.industry.sectors.assert_called_once_with(lang='vi')
        provider.industry.list.assert_called_once_with(lang='vi')


class AutomaticPeerTests(unittest.TestCase):
    def setUp(self):
        self.override = patch.object(engine,'_overrides',return_value=pd.DataFrame(columns=['TargetTicker','PeerTicker']))
        self.override.start()
        self.addCleanup(self.override.stop)

    def catalog(self, u=None):
        return engine._Catalog(metadata() if u is None else u, {})

    def test_small_industry_kept_and_inactive_removed(self):
        pool, label = engine._candidate_pool('AAA',metadata())
        self.assertEqual(set(pool.Ticker), {'AAA','BBB'})
        self.assertIn('cấp 4', label)

    def test_no_financial_data_still_has_metadata_peers(self):
        with patch.object(engine,'repair_snapshot',side_effect=lambda t,typ,base,root:dict(Ticker=t)):
            p = engine._selection('AAA',10,self.catalog())
        self.assertEqual(p.Ticker.tolist(), ['BBB'])
        self.assertTrue(p.SimilarityScore.isna().all())
        self.assertEqual(p.iloc[0].DataStatus, 'MISSING_VERIFIED_DATA')

    def test_same_period_and_basis_only_for_score(self):
        cat = self.catalog()
        cat.evidence = {'AAA':snap('AAA'), 'BBB':snap('BBB',period='2026-Q1')}
        p = engine._selection('AAA',10,cat)
        self.assertTrue(p.SimilarityScore.isna().all())
        cat.results.clear()
        cat.evidence['BBB'] = snap('BBB',basis='TTM')
        self.assertTrue(engine._selection('AAA',10,cat).SimilarityScore.isna().all())
        cat.results.clear()
        cat.evidence['BBB'] = snap('BBB',value=200)
        self.assertTrue(engine._selection('AAA',10,cat).SimilarityScore.notna().all())

    def test_shared_evidence_loaded_once_when_switching_ticker(self):
        cat = self.catalog()
        with patch.object(engine,'repair_snapshot',side_effect=lambda t,*a,**k:snap(t)) as read:
            engine._selection('AAA',10,cat)
            engine._selection('BBB',10,cat)
            engine._selection('AAA',10,cat)
        self.assertEqual(read.call_count,2)

    def test_unknown_industry_does_not_take_all_corporates(self):
        u = metadata()
        u.loc[u.Ticker.eq('AAA'), ['ICBCode2','ICBCode3','ICBCode4','Sector']] = ''
        pool,_ = engine._candidate_pool('AAA',u)
        self.assertEqual(pool.Ticker.tolist(), ['AAA'])

    def test_parent_fallback_when_no_other_leaf_member(self):
        pool,label = engine._candidate_pool('CCC',metadata())
        self.assertEqual(set(pool.Ticker), {'AAA','BBB','CCC'})
        self.assertIn('cấp 3', label)

    def test_collapsed_legacy_not_presented_as_level_four(self):
        u = metadata()
        for lv in range(1,5):
            u[f'ICBCode{lv}']='2000'
        pool,label = engine._candidate_pool('AAA',u)
        self.assertNotIn('cấp 4',label)
        self.assertTrue(pool.IndustryStatus.eq('LEGACY_ICB_REFRESH_REQUIRED').all())

    def test_all_map_includes_every_active_target_and_insurance(self):
        insurance = pd.DataFrame([dict(Ticker=t,EntityType='INSURANCE',Sector='Bảo hiểm',InsuranceSubtype='NONLIFE',InsuranceReportingSubtype='GROUP',Active=1) for t in ['BVH','PVI']])
        cat = self.catalog(pd.concat([metadata(),insurance],ignore_index=True))
        with TemporaryDirectory() as folder, patch.object(engine,'DATA',Path(folder)), patch.object(engine,'_catalog',return_value=cat), patch.object(engine,'peer_source_fingerprint',return_value='test'), patch.object(engine,'repair_snapshot',side_effect=lambda t,*a,**k:snap(t)):
            output = engine.build_dynamic_peer_map()
            summary = pd.read_csv(Path(folder)/'dynamic_peer_summary.csv')
            self.assertEqual(set(summary.Ticker), {'AAA','BBB','CCC','BVH','PVI'})
            self.assertEqual(output.loc[output.TargetTicker.eq('BVH'),'Ticker'].tolist(), ['PVI'])
            saved = engine._persisted('test',engine.signature(Path(folder)/'dynamic_peer_map.csv'),engine.signature(Path(folder)/'dynamic_peer_manifest.json'))
            self.assertIn('AAA',saved)
            self.assertIsNone(engine._persisted('changed',(),()))

    def test_empty_pool_never_falls_back_to_legacy_sector(self):
        from scripts.universal_data import peer_tickers
        from scripts.sector_benchmark_engine import industry_tickers
        with patch.object(engine,'dynamic_peer_tickers',return_value=['AAA']):
            self.assertEqual(peer_tickers('AAA'),['AAA'])
            self.assertEqual(industry_tickers('AAA'),['AAA'])

    def test_file_change_invalidates_shared_catalog_fingerprint(self):
        with TemporaryDirectory() as folder, patch.object(engine,'DATA',Path(folder)), patch.object(engine,'CFG',Path(folder)):
            (Path(folder)/'raw').mkdir()
            before = engine.peer_source_fingerprint()
            path = Path(folder)/'raw/AAA_balance.csv'
            path.write_text('Period,Value\n2026-Q2,100\n')
            after = engine.peer_source_fingerprint()
            self.assertNotEqual(before,after)
            path.unlink()
            self.assertEqual(before,engine.peer_source_fingerprint())

    def test_fingerprint_portable_between_windows_upload_and_cloud_clone(self):
        fingerprints=[]
        for content in ['Ticker\nAAA\n','Ticker\nAAA\n','Ticker\nBBB\n']:
            with TemporaryDirectory() as folder, patch.object(engine,'DATA',Path(folder)), patch.object(engine,'CFG',Path(folder)):
                (Path(folder)/'company_universe.csv').write_text(content)
                fingerprints.append(engine.peer_source_fingerprint())
        self.assertEqual(fingerprints[0],fingerprints[1])
        self.assertNotEqual(fingerprints[0],fingerprints[2])


class GlobalRefreshTests(unittest.TestCase):
    def test_global_download_resumes_only_failed_ticker(self):
        from contextlib import ExitStack
        from scripts import discover_listed_universe, universal_data
        u=metadata().query('Active == 1')
        with TemporaryDirectory() as folder, ExitStack() as stack:
            root=Path(folder)
            stack.enter_context(patch.object(refresh,'ROOT',root))
            stack.enter_context(patch.object(refresh,'DATA',root/'data'))
            stack.enter_context(patch.object(refresh,'STATE',root/'state.json'))
            stack.enter_context(patch.object(discover_listed_universe,'main'))
            stack.enter_context(patch.object(icb,'apply_industry_classification'))
            stack.enter_context(patch.object(universal_data,'universe',return_value=u))
            build=stack.enter_context(patch.object(engine,'build_dynamic_peer_map'))
            calls=[]
            fail={'BBB'}
            def download(cmd, cwd):
                ticker=cmd[2]
                calls.append(ticker)
                if ticker in fail:
                    return 1
                for path in refresh.required_raw_paths(ticker,'CORPORATE'):
                    path.parent.mkdir(parents=True,exist_ok=True)
                    pd.DataFrame([{'period':'2026-Q2','id':'BS_TOTAL_ASSETS','value':100}]).to_csv(path,index=False)
                return 0
            stack.enter_context(patch.object(refresh.subprocess,'call',side_effect=download))
            self.assertEqual(refresh.main(['--ticker-delay','0']),2)
            self.assertEqual(calls,['AAA','BBB','CCC'])
            fail.clear()
            calls.clear()
            self.assertEqual(refresh.main(['--ticker-delay','0']),0)
            self.assertEqual(calls,['BBB'])
            self.assertEqual(build.call_count,2)
            state=json.loads((root/'state.json').read_text())
            self.assertTrue(all(r['Status']=='DOWNLOADED' for r in state.values()))

    def test_catalog_only_never_downloads_financials(self):
        from scripts import discover_listed_universe, universal_data
        with TemporaryDirectory() as folder, patch.object(refresh,'STATE',Path(folder)/'state.json'), patch.object(discover_listed_universe,'main') as listing, patch.object(icb,'apply_industry_classification') as classify, patch.object(universal_data,'universe',return_value=metadata()), patch.object(engine,'build_dynamic_peer_map') as build, patch.object(refresh.subprocess,'call') as download:
            self.assertEqual(refresh.main(['--catalog-only']),0)
            listing.assert_called_once()
            classify.assert_called_once()
            build.assert_called_once()
            download.assert_not_called()

    def test_bank_does_not_require_cashflow_unavailable_in_bank_parser(self):
        paths = refresh.required_raw_paths('VCB','BANK')
        self.assertEqual(len(paths),3)
        self.assertFalse(any('cashflow' in p.name for p in paths))
        self.assertEqual(len(refresh.required_raw_paths('HPG','CORPORATE')),4)

    def test_resumes_recent_success_and_retries_missing_or_failed(self):
        state={'AAA':{'Status':'DOWNLOADED','DownloadedAtEpoch':1000}}
        with patch.object(refresh,'raw_status',return_value=(True,'2026-Q2')):
            self.assertFalse(refresh.needs_refresh('AAA','CORPORATE',state,7,now=1001))
            self.assertTrue(refresh.needs_refresh('BBB','CORPORATE',state,7,now=1001))
            self.assertTrue(refresh.needs_refresh('AAA','CORPORATE',state,7,now=1000+8*86400))
        with patch.object(refresh,'raw_status',return_value=(False,'')):
            self.assertTrue(refresh.needs_refresh('AAA','CORPORATE',state,7,now=1001))


if __name__ == '__main__':
    unittest.main()
