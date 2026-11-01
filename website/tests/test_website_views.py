import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAMP = '2026-11-01T14:15:48.963Z'
NOW = '2026-11-01T15:00:00Z'
ENDPOINT = 'https://logscience-views.example.workers.dev/views'
ORIGIN = 'https://xiaoma2000.github.io'
BASE = '/LogScience.github.io'


class WebsiteViewsTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'tools/website_views.py'
        self.assertTrue(path.is_file(), 'A build-time confirmed website snapshot collector is required')
        spec = importlib.util.spec_from_file_location('website_views', path)
        self.views = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.views)
        self.config = {'site_code':'logscience-test', 'repository_views':15,
                       'website_views':24, 'website_updated_at':STAMP, 'counter_endpoint':ENDPOINT}

    def previous(self, repo=17, website=26, stamp='2026-11-01T14:30:00Z'):
        return {'schema':1, 'site_code':'logscience-test', 'repository_views':repo,
                'website_views':website, 'total':repo+website,
                'website_updated_at':stamp, 'updated_at':'2026-11-01T14:31:00Z'}

    def test_fresh_worker_result_is_added_to_repository_once(self):
        result, warnings = self.views.combine(self.config, None, {'count':28,'updated_at':NOW}, NOW)
        self.assertEqual(result['total'],43)
        self.assertEqual(result['website_views'],28)
        self.assertEqual(result['website_updated_at'],NOW)
        self.assertEqual(warnings,[])

    def test_network_failure_preserves_deployed_maxima_and_the_original_source_time(self):
        result, _ = self.views.combine(self.config, self.previous(), None, NOW)
        self.assertEqual(result['total'],43)
        self.assertEqual(result['website_updated_at'],'2026-11-01T14:30:00Z')
        self.assertEqual(result['updated_at'],NOW)

    def test_lower_worker_result_cannot_reset_confirmed_views_or_relabel_old_data_fresh(self):
        result, _ = self.views.combine(self.config, self.previous(), {'count':0,'updated_at':NOW}, NOW)
        self.assertEqual(result['total'],43)
        self.assertEqual(result['website_updated_at'],'2026-11-01T14:30:00Z')

    def test_bad_counts_future_dates_and_foreign_recovery_are_ignored(self):
        for bad in [{'count':True,'updated_at':NOW},{'count':-1,'updated_at':NOW},
                    {'count':2**53,'updated_at':NOW},{'count':50,'updated_at':'2027-01-01T00:00:00Z'}]:
            result, warnings = self.views.combine(self.config, None, bad, NOW)
            self.assertEqual(result['total'],39)
            self.assertTrue(warnings)
        foreign = {**self.previous(), 'site_code':'another-site'}
        result, warnings = self.views.combine(self.config, foreign, None, NOW)
        self.assertEqual(result['total'],39)
        self.assertTrue(warnings)

    def test_config_is_updated_without_mutating_original(self):
        result, _ = self.views.combine(self.config, None, {'count':28,'updated_at':NOW}, NOW)
        config = self.views.update_config(self.config, result)
        self.assertEqual(config['website_views'],28)
        self.assertEqual(self.config['website_views'],24)

    def test_build_writes_same_origin_json_and_injects_confirmed_html_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '_data').mkdir()
            config_path = root / '_data/page_views.json'
            config_path.write_text(json.dumps(self.config),encoding='utf-8')
            calls=[]
            def read(url):
                calls.append(url)
                if url == ENDPOINT: return {'count':28,'updated_at':NOW}
                self.assertEqual(url,ORIGIN + BASE + '/metrics/page-views.json')
                return self.previous()
            result, _ = self.views.build(root, ORIGIN, BASE, reader=read, now=NOW)
            public = json.loads((root / 'metrics/page-views.json').read_text(encoding='utf-8'))
            self.assertEqual(public['total'],45)
            self.assertEqual(public,result)
            self.assertEqual(json.loads(config_path.read_text(encoding='utf-8'))['website_views'],28)
            self.assertEqual(len(calls),2)

    def test_build_refuses_a_new_deployment_when_no_recovery_or_current_count_is_available(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root / '_data').mkdir()
            (root / '_data/page_views.json').write_text(json.dumps(self.config),encoding='utf-8')
            def offline(url): raise OSError('offline')
            with self.assertRaisesRegex(ValueError,'recovery'):
                self.views.build(root, ORIGIN, BASE, reader=offline, now=NOW)
            self.assertFalse((root / 'metrics/page-views.json').exists())

    def test_artifact_preserves_a_higher_count_when_both_network_sources_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root / '_data').mkdir()
            (root / '_data/page_views.json').write_text(json.dumps(self.config),encoding='utf-8')
            state = root / 'local/traffic-state'; state.mkdir(parents=True)
            (state / 'page-views.json').write_text(json.dumps(self.previous(17,80)),encoding='utf-8')
            def offline(url): raise OSError('offline')
            result, _ = self.views.build(root, ORIGIN, BASE, reader=offline, now=NOW)
            self.assertEqual(result['total'],97)
            self.assertEqual(result['website_updated_at'],'2026-11-01T14:30:00Z')
            self.assertEqual(json.loads((state / 'page-views.json').read_text())['total'],97)

    def test_build_rejects_foreign_recovery_origins_and_unsafe_worker_urls(self):
        with self.assertRaises(ValueError):
            self.views.build(ROOT,'https://evil.test',BASE,reader=lambda url:None,now=NOW)
        for endpoint in ['http://worker.workers.dev/views','https://evil.test/views',
                         ENDPOINT+'?token=secret','https://user:pass@worker.workers.dev/views']:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory); (root / '_data').mkdir()
                (root / '_data/page_views.json').write_text(json.dumps({**self.config,'counter_endpoint':endpoint}))
                with self.assertRaises(ValueError):
                    self.views.build(root,ORIGIN,BASE,reader=lambda url:None,now=NOW)


if __name__ == '__main__':
    unittest.main()
