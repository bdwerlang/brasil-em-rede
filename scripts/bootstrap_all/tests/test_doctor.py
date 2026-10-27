import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bootstrap_all.doctor import diagnose


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        (self.root / 'config').mkdir()
        (self.root / 'etl/src/bracc_etl').mkdir(parents=True)
        (self.root / 'data/example').mkdir(parents=True)
        (self.root / 'data/example/input.csv').touch()
        (self.root / 'config/source_aliases.json').write_text(json.dumps({'sources': [{'source_id': 'example', 'runner_name': 'runner'}]}))
        (self.root / 'etl/src/bracc_etl/runner.py').write_text('PIPELINES: dict = {"runner": Pipeline}\n')
        self.contract = {'expected_implemented_count': 1, 'sources': [{'pipeline_id': 'example', 'acquisition_mode': 'file_manifest', 'required_inputs': ['data/example/input.csv']}]}

    def test_valid_and_missing_input(self):
        self.assertEqual(diagnose(self.root, self.contract, {'example'}), [])
        (self.root / 'data/example/input.csv').unlink()
        self.assertTrue(any('missing input' in e for e in diagnose(self.root, self.contract, {'example'})))

    def test_detects_registry_runner_and_duplicate_divergence(self):
        self.assertTrue(any('registry mismatch' in e for e in diagnose(self.root, self.contract, {'other'})))
        (self.root / 'etl/src/bracc_etl/runner.py').write_text('PIPELINES: dict = {"other": Pipeline}\n')
        self.assertTrue(any('runner mismatch' in e for e in diagnose(self.root, self.contract, {'example'})))
        self.contract['sources'].append(self.contract['sources'][0])
        self.assertTrue(any('unique' in e for e in diagnose(self.root, self.contract, {'example'})))

    def test_rejects_missing_command(self):
        source = self.contract['sources'][0]
        source['acquisition_mode'] = 'script_download'
        source['download_commands'] = ['python3 /workspace/scripts/missing.py']
        self.assertTrue(any('unsupported or missing' in e for e in diagnose(self.root, self.contract, {'example'})))

    def test_blocked_source_does_not_report_missing_input(self):
        self.contract['sources'][0]['acquisition_mode'] = 'blocked_external'
        (self.root / 'data/example/input.csv').unlink()
        self.assertEqual(diagnose(self.root, self.contract, {'example'}), [])

    def test_download_entrypoint_and_command_are_registered(self):
        runner = self.root / 'etl/src/bracc_etl/runner.py'
        runner.write_text("PIPELINES: dict = {\"runner\": Pipeline}\n@click.group()\ndef cli(): pass\n@cli.command()\n@click.option(' --output-dir'.strip())\n@click.option('--files')\n@click.option('--skip-existing/--no-skip-existing')\ndef download(): pass\n")
        # Use literal Click options as in the actual runner.
        runner.write_text(runner.read_text().replace("' --output-dir'.strip()", "'--output-dir'"))
        project = self.root / 'etl/pyproject.toml'
        project.write_text('[project.scripts]\nbracc-etl = "bracc_etl.runner:cli"\n')
        source = self.contract['sources'][0]
        source['acquisition_mode'] = 'script_download'
        source['download_commands'] = ['cd /workspace/etl && bracc-etl download --output-dir ../data/cnpj --files 10 --skip-existing']
        self.assertEqual(diagnose(self.root, self.contract, {'example'}), [])
        runner.write_text(runner.read_text().replace('def download', 'def renamed'))
        self.assertTrue(any('unsupported or missing' in e for e in diagnose(self.root, self.contract, {'example'})))
        runner.write_text(runner.read_text().replace('def renamed', 'def download'))
        project.write_text('[project.scripts]\nbracc-etl = "bracc_etl.runner:missing"\n')
        self.assertTrue(any('unsupported or missing' in e for e in diagnose(self.root, self.contract, {'example'})))

    def test_cli_doctor_never_runs_commands(self):
        repo = Path(__file__).resolve().parents[3]
        (self.root / 'docs').mkdir()
        (self.root / 'docs/source_registry_br_v1.csv').write_text('pipeline_id,in_universe_v1,implementation_state\nexample,true,implemented\n')
        (self.root / 'config/bootstrap_all_contract.yml').write_text(json.dumps(self.contract))
        result = subprocess.run([sys.executable, str(repo / 'scripts/run_bootstrap_all.py'), '--repo-root', str(self.root), '--doctor', '--yes-reset'], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['config', 'data', 'docs', 'etl'])


if __name__ == '__main__':
    unittest.main()
