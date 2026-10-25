import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('render', ROOT/'scripts/render.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.items = m.inventory(ROOT/'instances.example.json')

    def test_isolated_instances(self):
        config = m.render(self.items)
        self.assertNotIn('ports', config['services']['db'])
        self.assertIn('--event-scheduler=DISABLED', config['services']['db']['command'])
        for item in self.items:
            name = item['name']
            for role in ('web', 'cron', 'worker'):
                service = config['services'][name+'-'+role]
                self.assertEqual(service['networks'], ['db_'+name, 'outbound_'+name])
                self.assertEqual(service['secrets'], [{'source':'db_mautic_'+name,'target':'database_password'}])
                self.assertNotIn('MAUTIC_DB_PASSWORD', service['environment'])
                if role == 'web':
                    self.assertEqual(service['ports'], [f"127.0.0.1:{item['port']}:80"])
                else:
                    self.assertEqual(service['profiles'], ['jobs'])
                self.assertFalse(any(v.endswith(':/var/www/html') for v in service['volumes']))
                self.assertIn(name+'_files:/var/www/html/docroot/media/files', service['volumes'])
                self.assertIn(name+'_images:/var/www/html/docroot/media/images', service['volumes'])
            self.assertTrue(config['networks']['db_'+name]['internal'])
        first = config['services']['marketing-web']; second = config['services']['sales-web']
        self.assertFalse(set(first['volumes']) & set(second['volumes']))

    def test_invalid_inventory_rejected(self):
        for changes in ({'name':'x;id'}, {'domain':'x\nproxy_pass attacker;'}, {'port':80},
                        {'trusted_proxies':['REMOTE_ADDR']}, {'trusted_proxies':['0.0.0.0/0']}):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                items=copy.deepcopy(self.items); items[0].update(changes)
                p=Path(tmp)/'config';p.write_text(json.dumps({'instances':items}))
                with self.assertRaises(ValueError):m.inventory(p)

    def test_duplicates_rejected(self):
        for field in ('name','port','domain'):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as tmp:
                items=copy.deepcopy(self.items);items[1][field]=items[0][field]
                p=Path(tmp)/'config';p.write_text(json.dumps({'instances':items}))
                with self.assertRaises(ValueError):m.inventory(p)

    def test_secret_initialization_preserves_existing_passwords(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'secrets';m.initialize(self.items,root)
            before={p.name:p.read_text() for p in root.iterdir()}
            m.initialize(self.items,root)
            self.assertEqual(before,{p.name:p.read_text() for p in root.iterdir()})
            self.assertEqual(root.stat().st_mode & 0o777,0o700)
            for p in root.iterdir():
                self.assertEqual(p.stat().st_mode & 0o777,0o600)
                self.assertRegex(p.read_text(),r'^[a-f0-9]{48}\n$')
