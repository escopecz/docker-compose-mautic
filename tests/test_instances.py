import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('instances', Path(__file__).resolve().parents[1] / 'scripts/instances.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class IsolationTests(unittest.TestCase):
    def test_application_cannot_manage_shared_database(self):
        for item in m.inventory().values():
            compose = m.app_compose(item)
            self.assertEqual(set(compose['services']), {'web', 'cron', 'worker'})
            self.assertTrue(all(v['external'] for v in compose['volumes'].values()))
            self.assertEqual(compose['services']['web']['ports'], [f"127.0.0.1:{item['port']}:80"])
            for role in ('cron', 'worker'):
                self.assertEqual(compose['services'][role]['profiles'], ['jobs'])
            for service in compose['services'].values():
                self.assertEqual(service['environment']['DOCKER_MAUTIC_RUN_MIGRATIONS'], 'false')

    def test_database_has_no_published_ports_or_application_volumes(self):
        compose = m.database_compose(m.inventory())
        self.assertNotIn('ports', compose['services']['mysql'])
        self.assertEqual(set(compose['volumes']), {'data'})
        self.assertTrue(all(n['external'] for n in compose['networks'].values()))

    def test_reject_unsafe_inventory(self):
        for changes in ({'port': 3306}, {'host': 'attacker.example'}, {'database': 'mysql'},
                        {'image': 'mautic/mautic:latest'}, {'status': 'ready'},
                        {'migration_path': ['4.4.8', '7.2.1']}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'instances').mkdir()
                item = copy.deepcopy(m.inventory()['cronfig'])
                item.update(changes)
                (root / 'instances/cronfig.json').write_text(json.dumps(item))
                with self.assertRaises(ValueError):
                    m.inventory(root)

    def test_duplicate_ports_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'instances').mkdir()
            for item in m.inventory().values():
                item['port'] = 8001
                (root / f"instances/{item['id']}.json").write_text(json.dumps(item))
            with self.assertRaises(ValueError):
                m.inventory(root)


if __name__ == '__main__':
    unittest.main()
