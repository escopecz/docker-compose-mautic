import gzip,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class CronfigDeploymentTests(unittest.TestCase):
    def test_stage_is_isolated_and_never_starts_jobs_or_automatic_migrations(self):
        config=json.loads(subprocess.check_output([sys.executable,str(ROOT/'scripts/cronfig-compose.py')]))
        self.assertEqual(list(config['services']),['web'])
        web=config['services']['web']
        self.assertEqual(web['networks'],['database'])
        self.assertEqual(web['entrypoint'],['/opt/cronfig-entrypoint.sh'])
        self.assertEqual(web['environment']['MAUTIC_TABLE_PREFIX'],'mautic_')
        self.assertEqual(web['ports'],['127.0.0.1:8002:80'])
        self.assertNotIn('mysql',config['services'])
        self.assertFalse(any(v.split(':')[1]=='/var/www/html' for v in web['volumes']))
    def test_live_adds_outbound_without_changing_database_or_storage(self):
        def render(*args):return json.loads(subprocess.check_output([sys.executable,str(ROOT/'scripts/cronfig-compose.py'),*args]))
        stage=render();live=render('--live')
        self.assertEqual(live['services']['web']['networks'],['database','outbound'])
        self.assertEqual(stage['services']['web']['volumes'],live['services']['web']['volumes'])
        self.assertEqual(stage['networks']['database'],live['networks']['database'])
    def test_dump_preserves_routine_without_root_definer_and_rejects_globals(self):
        routine='CREATE DEFINER=`root`@`%` PROCEDURE `mautic_cleanup`()\nbegin SELECT 1; end;;\n'
        for prefix,expected in [('',0),('USE another_database;\n',1),('GRANT ALL ON *.* TO evil;\n',1)]:
            with self.subTest(prefix=prefix),tempfile.TemporaryDirectory() as tmp:
                src=Path(tmp)/'in.gz';dst=Path(tmp)/'out.gz'
                with gzip.open(src,'wt') as f:f.write(prefix+routine)
                result=subprocess.run([sys.executable,str(ROOT/'scripts/cronfig-dump.py'),str(src),str(dst)],capture_output=True)
                self.assertEqual(result.returncode,expected)
                if expected==0:
                    with gzip.open(dst,'rt') as f:sql=f.read()
                    self.assertIn('SQL SECURITY INVOKER',sql);self.assertNotIn('DEFINER=',sql)
