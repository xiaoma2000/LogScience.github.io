import copy
from datetime import date
import importlib.util
from pathlib import Path
import unittest
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('repository_traffic', ROOT / 'tools/repository_traffic.py')
traffic = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(traffic)
REPO = 'xiaoma2000/LogScience.github.io'


def state(days):
    return {'schema':1, 'repository':REPO, 'metric':'repository_page_views',
            'coverage_start':'2026-10-25', 'days':days}


def snapshot(days):
    return {'count':sum(days.values()), 'uniques':1,
            'views':[{'timestamp':d+'T00:00:00Z', 'count':n, 'uniques':1} for d,n in days.items()]}


class TrafficTests(unittest.TestCase):
    def test_overlap_is_replaced_not_added_and_retries_are_idempotent(self):
        seed=state({'2026-10-25':14,'2026-10-26':1})
        report=snapshot({'2026-10-26':2,'2026-10-27':3})
        result=traffic.merge_reports(REPO,[seed],report)
        self.assertEqual(result['total'],19)
        self.assertEqual(traffic.merge_reports(REPO,[result],report),result)

    def test_lower_revised_counts_cannot_remove_previously_observed_views(self):
        result=traffic.merge_reports(REPO,[state({'2026-10-25':14,'2026-10-26':1})],
                                     snapshot({'2026-10-25':10,'2026-10-26':1}))
        self.assertEqual(result['total'],15)

    def test_recovery_sources_combine_by_day_without_doubling(self):
        result=traffic.merge_reports(REPO,[state({'2026-10-25':14,'2026-10-26':1}),
            state({'2026-10-25':14,'2026-10-26':3})],snapshot({'2026-10-27':2}))
        self.assertEqual(result['total'],19)

    def test_missing_days_fail_instead_of_inventing_older_views(self):
        with self.assertRaisesRegex(ValueError,'Missing'):
            traffic.merge_reports(REPO,[state({'2026-10-25':14})],snapshot({'2026-10-27':3}))

    def test_invalid_or_foreign_ledgers_are_rejected(self):
        good=state({'2026-10-25':14})
        for mutate in (lambda s:s.update(repository='another/repo'),
                       lambda s:s.update(metric='clones'),
                       lambda s:s['days'].update({'2026-10-25':True}),
                       lambda s:s['days'].update({'2026-10-25':-1}),
                       lambda s:s['days'].update({'2026-02-31':1})):
            bad=copy.deepcopy(good); mutate(bad)
            with self.assertRaises(ValueError): traffic.merge_reports(REPO,[bad],snapshot({'2026-10-25':14}))

    def test_invalid_snapshot_duplicate_dates_or_inconsistent_total_are_rejected(self):
        for report in ({'count':10,'views':[]}, snapshot({'2026-10-25':-1}),
                       {'count':2,'views':[{'timestamp':'2026-10-25T00:00:00Z','count':1}]*2}):
            with self.assertRaises(ValueError):
                traffic.merge_reports(REPO,[state({'2026-10-25':14})],report)

    def test_reports_before_the_user_seed_period_do_not_expand_scope(self):
        result=traffic.merge_reports(REPO,[state({'2026-10-25':14})],snapshot({'2026-10-24':90,'2026-10-25':14}))
        self.assertEqual(result['total'],14)

    def test_build_injection_preserves_service_settings_and_original_config(self):
        original={'site_code':'logscience-lab','repository_views':15,'enabled':True}
        ledger=traffic.merge_reports(REPO,[state({'2026-10-25':14})],snapshot({'2026-10-26':3}))
        result=traffic.update_config(original,ledger)
        self.assertEqual(result['repository_views'],17)
        self.assertEqual(result['site_code'],'logscience-lab')
        self.assertEqual(original['repository_views'],15)

    def test_artifact_selection_ignores_expired_foreign_and_wrong_branch_data(self):
        records=[{'id':4,'name':traffic.ARTIFACT,'expired':False,'size_in_bytes':200,
                  'workflow_run':{'id':20,'head_branch':'master','head_repository_id':7}},
                 {'id':5,'name':traffic.ARTIFACT,'expired':True,'size_in_bytes':200,
                  'workflow_run':{'id':21,'head_branch':'master','head_repository_id':7}}]
        self.assertEqual(traffic.select_artifact(records,7)['id'],4)
        self.assertIsNone(traffic.select_artifact(records,8))

    def test_failed_download_ignores_partial_file_and_recovers_from_deployed_ledger(self):
        seed=state({'2026-10-25':14})
        deployed=state({'2026-10-25':14,'2026-10-26':1,'2026-10-27':2})
        (ROOT/'local').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'local') as folder:
            path=Path(folder)/'ledger.json'; path.write_text('{partial',encoding='utf-8')
            sources,warnings=traffic.recovery_states(REPO,seed,path,False,deployed)
            result=traffic.merge_reports(REPO,sources,snapshot({'2026-10-28':1}))
        self.assertEqual(result['total'],18)

    def test_invalid_artifact_cannot_block_an_independently_valid_recovery(self):
        seed=state({'2026-10-25':14})
        (ROOT/'local').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'local') as folder:
            path=Path(folder)/'ledger.json'; path.write_text('{bad',encoding='utf-8')
            sources,warnings=traffic.recovery_states(REPO,seed,path,True,
                         state({'2026-10-25':14,'2026-10-26':1}))
            result=traffic.merge_reports(REPO,sources,snapshot({'2026-10-27':2}))
        self.assertEqual(result['total'],17)
        self.assertTrue(warnings)

    def test_sparse_report_zero_fills_only_days_in_the_current_rolling_window(self):
        result=traffic.merge_reports(REPO,[state({'2026-10-25':14})],
            snapshot({'2026-10-28':2}),as_of=date(2026,10,28))
        self.assertEqual(result['total'],16)
        self.assertEqual(result['days']['2026-10-26'],0)

    def test_empty_zero_report_is_valid_without_losing_historical_views(self):
        result=traffic.merge_reports(REPO,[state({'2026-10-25':14,'2026-10-26':1})],
            {'count':0,'views':[]},as_of=date(2026,10,28))
        self.assertEqual(result['total'],15)

    def test_zero_window_cannot_fill_unknown_days_older_than_fourteen_days(self):
        with self.assertRaisesRegex(ValueError,'Missing'):
            traffic.merge_reports(REPO,[state({'2026-10-25':14})],
                {'count':0,'views':[]},as_of=date(2026,11,20))


if __name__ == '__main__': unittest.main()
