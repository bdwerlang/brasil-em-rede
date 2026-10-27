import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'infra' / 'scripts'
spec = importlib.util.spec_from_file_location('readiness', SCRIPTS / 'api-readiness.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class EnvironmentTests(unittest.TestCase):
    def test_readiness_requires_catalog_and_connected_database(self):
        registry = types.ModuleType('bracc.services.source_registry')
        registry.load_source_registry = lambda: [types.SimpleNamespace(id='synthetic')]
        response = io.BytesIO(json.dumps({'neo4j': 'connected'}).encode())
        with patch.dict(sys.modules, {'bracc': types.ModuleType('bracc'),
                'bracc.services': types.ModuleType('bracc.services'),
                'bracc.services.source_registry': registry}), patch.object(probe, 'urlopen', return_value=response):
            self.assertTrue(probe.ready())
            registry.load_source_registry = lambda: []
            self.assertFalse(probe.ready())
            registry.load_source_registry = lambda: [types.SimpleNamespace(id='synthetic')]
            with patch.object(probe, 'urlopen', return_value=io.BytesIO(b'{"neo4j":"error"}')):
                self.assertFalse(probe.ready())
            with patch.object(probe, 'urlopen', side_effect=OSError('offline')):
                with self.assertRaises(OSError):
                    probe.ready()

    def test_restore_preflight_never_changes_files_and_rejects_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            backup = root / 'synthetic.dump'
            backup.write_bytes(b'synthetic')
            destination = root / 'destination'
            destination.mkdir()
            cmd = [sys.executable, str(SCRIPTS / 'restore-preflight.py'), str(backup), str(destination)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn('restore: not performed', result.stdout)
            self.assertEqual(list(destination.iterdir()), [])
            (destination / 'existing').write_text('preserved')
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual((destination / 'existing').read_text(), 'preserved')

    def test_seed_uses_fresh_project_and_refuses_existing_volume(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = root / 'docker'
            fake.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$FAKE_LOG\"\n"
                            "if [ \"$1\" = volume ]; then [ \"$FAKE_EXISTS\" = yes ]; exit $?; fi\n"
                            "exit 0\n")
            fake.chmod(0o755)
            env = dict(os.environ, PATH=f'{root}:{os.environ["PATH"]}',
                       DEMO_NEO4J_PASSWORD='synthetic', FAKE_LOG=str(root / 'calls'), FAKE_EXISTS='no')
            run = lambda: subprocess.run(['bash', str(SCRIPTS / 'seed-dev.sh')], env=env, capture_output=True, text=True)
            result = run()
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = (root / 'calls').read_text().splitlines()
            self.assertEqual(len(calls), 3)
            self.assertTrue(calls[0].startswith('volume inspect bracc-demo-'))
            self.assertIn(' up -d --wait neo4j', calls[1])
            self.assertIn('cypher-shell -u neo4j -p "$DEMO_DB_PASSWORD"', calls[2])
            project = calls[0].split()[2].removesuffix('_demo-data')
            self.assertIn(f'--project-name {project}', calls[1])
            self.assertIn(f'--project-name {project}', calls[2])
            (root / 'calls').unlink()
            env['FAKE_EXISTS'] = 'yes'
            self.assertNotEqual(run().returncode, 0)
            self.assertEqual(len((root / 'calls').read_text().splitlines()), 1)

if __name__ == '__main__':
    unittest.main()
