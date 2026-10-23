import gzip,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ChimpinoDeploymentTests(unittest.TestCase):
    def test_chimpino_has_separate_database_network_and_no_jobs(self):
        config=json.loads(subprocess.check_output([sys.executable,str(ROOT/'scripts/chimpino-compose.py')]))
        self.assertEqual(list(config['services']),['web'])
        web=config['services']['web']
        self.assertEqual(web['environment']['MAUTIC_TABLE_PREFIX'],'')
        self.assertEqual(web['ports'],['127.0.0.1:8003:80'])
        self.assertEqual(web['networks'],['database'])
        self.assertEqual(config['networks']['database']['name'],'mautic-db-chimpino')
        self.assertTrue(any('/StripeBundle:' in v for v in web['volumes']))
        self.assertTrue(any('/CronfigBundle:' in v for v in web['volumes']))
        self.assertFalse(any('/AiBundle:' in v for v in web['volumes']))
    def test_dump_rejects_cross_schema_and_stored_programs(self):
        for sql,expected in [('CREATE TABLE leads (id INT);\n',0),('USE other;\n',1),('GRANT ALL ON *.* TO evil;\n',1),('CREATE PROCEDURE cleanup() SELECT 1;\n',1),('CREATE DEFINER=`root`@`%` VIEW v AS SELECT 1;\n',1)]:
            with self.subTest(sql=sql),tempfile.TemporaryDirectory() as tmp:
                src=Path(tmp)/'in.gz';dst=Path(tmp)/'out.gz'
                with gzip.open(src,'wt') as f:f.write(sql)
                result=subprocess.run([sys.executable,str(ROOT/'scripts/chimpino-dump.py'),str(src),str(dst)],capture_output=True)
                self.assertEqual(result.returncode,expected)
