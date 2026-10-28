import json
import os
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
        runner = self.root / 'etl/src/bracc_etl/runner.py'
        runner.write_text('''class Pipeline: pass
PIPELINES: dict = {"runner": Pipeline}
@click.group()
def cli(): pass
@cli.command()
@click.option("--source")
@click.option("--neo4j-uri")
@click.option("--neo4j-user")
@click.option("--neo4j-password")
@click.option("--neo4j-database")
@click.option("--data-dir")
@click.option("--linking-tier")
def run(): pass
''')
        (self.root / 'etl/pyproject.toml').write_text('[project.scripts]\nbracc-etl = "bracc_etl.runner:cli"\n')
        self.contract = {'expected_implemented_count': 1, 'sources': [{'pipeline_id': 'example', 'acquisition_mode': 'file_manifest', 'required_inputs': ['data/example/input.csv']}]}

    def test_valid_and_missing_input(self):
        self.assertEqual(diagnose(self.root, self.contract, {'example'}), [])
        (self.root / 'data/example/input.csv').unlink()
        self.assertTrue(any('missing input' in e for e in diagnose(self.root, self.contract, {'example'})))

    def test_directory_does_not_satisfy_required_file_input(self):
        (self.root / 'data/example/input.csv').unlink()
        (self.root / 'data/example/input.csv').mkdir()
        self.assertTrue(any('missing input' in e for e in diagnose(self.root, self.contract, {'example'})))

    def test_detects_registry_runner_and_duplicate_divergence(self):
        self.assertTrue(any('registry mismatch' in e for e in diagnose(self.root, self.contract, {'other'})))
        (self.root / 'etl/src/bracc_etl/runner.py').write_text('PIPELINES: dict = {"other": Pipeline}\n')
        self.assertTrue(any('runner mismatch' in e for e in diagnose(self.root, self.contract, {'example'})))
        self.contract['sources'].append(self.contract['sources'][0])
        self.assertTrue(any('unique' in e for e in diagnose(self.root, self.contract, {'example'})))

    def test_detects_duplicate_runner_keys(self):
        (self.root / 'etl/src/bracc_etl/runner.py').write_text('class Pipeline: pass\nPIPELINES: dict = {"runner": Pipeline, "runner": Pipeline}\n')
        self.assertTrue(any('duplicate keys' in e for e in diagnose(self.root, self.contract, {'example'})))

    def test_rejects_missing_command(self):
        source = self.contract['sources'][0]
        source['acquisition_mode'] = 'script_download'
        source['download_commands'] = ['python3 /workspace/scripts/missing.py']
        self.assertTrue(any('unsupported or missing' in e for e in diagnose(self.root, self.contract, {'example'})))

    def test_rejects_string_download_commands_without_iterating_characters(self):
        source = self.contract['sources'][0]
        source['acquisition_mode'] = 'script_download'
        source['download_commands'] = 'python3 /workspace/scripts/missing.py'
        issues = diagnose(self.root, self.contract, {'example'})
        self.assertTrue(any('download_commands must be a list of strings' in e for e in issues))
        self.assertFalse(any('unsupported or missing download command' in e for e in issues))

    def test_rejects_download_commands_on_manifest_source(self):
        source = self.contract['sources'][0]
        source['download_commands'] = ['python3 /workspace/scripts/missing.py']
        self.assertTrue(any('require script_download mode' in e for e in diagnose(self.root, self.contract, {'example'})))

    def test_checks_physical_pipeline_modules_and_imported_classes(self):
        runner = self.root / 'etl/src/bracc_etl/runner.py'
        runner.write_text('from bracc_etl.pipelines.example import ExamplePipeline\nPIPELINES: dict = {"runner": ExamplePipeline}\n')
        issues = diagnose(self.root, self.contract, {'example'})
        self.assertTrue(any('missing pipeline module' in e for e in issues))
        module = self.root / 'etl/src/bracc_etl/pipelines/example.py'
        module.parent.mkdir(parents=True)
        module.write_text('class OtherPipeline: pass\n')
        issues = diagnose(self.root, self.contract, {'example'})
        self.assertTrue(any('missing ExamplePipeline' in e for e in issues))

    def test_checks_pipeline_values_resolve_to_defined_classes(self):
        (self.root / 'etl/src/bracc_etl/runner.py').write_text('PIPELINES: dict = {"runner": MissingPipeline}\n')
        issues = diagnose(self.root, self.contract, {'example'})
        self.assertTrue(any('PIPELINES references undefined class MissingPipeline' in e for e in issues))

    def test_requires_runner_cli_options_used_by_bootstrap(self):
        runner = self.root / 'etl/src/bracc_etl/runner.py'
        runner.write_text(runner.read_text().replace('@click.option("--data-dir")\n', ''))
        issues = diagnose(self.root, self.contract, {'example'})
        self.assertTrue(any('ETL run command is missing' in e for e in issues))

    def test_blocked_source_does_not_report_missing_input(self):
        self.contract['sources'][0]['acquisition_mode'] = 'blocked_external'
        (self.root / 'data/example/input.csv').unlink()
        self.assertEqual(diagnose(self.root, self.contract, {'example'}), [])

    def test_download_entrypoint_and_command_are_registered(self):
        runner = self.root / 'etl/src/bracc_etl/runner.py'
        runner.write_text("class Pipeline: pass\nPIPELINES: dict = {\"runner\": Pipeline}\n@click.group()\ndef cli(): pass\n@cli.command()\n@click.option('--source')\n@click.option('--neo4j-uri')\n@click.option('--neo4j-user')\n@click.option('--neo4j-password')\n@click.option('--neo4j-database')\n@click.option('--data-dir')\n@click.option('--linking-tier')\ndef run(): pass\n@cli.command()\n@click.option(' --output-dir'.strip())\n@click.option('--files')\n@click.option('--skip-existing/--no-skip-existing')\ndef download(): pass\n")
        # Use literal Click options as in the actual runner.
        runner.write_text(runner.read_text().replace("' --output-dir'.strip()", "'--output-dir'"))
        project = self.root / 'etl/pyproject.toml'
        self.contract['sources'][0]['pipeline_id'] = 'cnpj'
        (self.root / 'config/source_aliases.json').write_text(json.dumps({'sources': [{'source_id': 'cnpj', 'runner_name': 'runner'}]}))
        source = self.contract['sources'][0]
        source['acquisition_mode'] = 'script_download'
        source['download_commands'] = ['cd /workspace/etl && bracc-etl download --output-dir ../data/cnpj --files 10 --skip-existing']
        self.assertEqual(diagnose(self.root, self.contract, {'cnpj'}), [])
        runner.write_text(runner.read_text().replace('def download', 'def renamed'))
        self.assertTrue(any('unsupported or missing' in e for e in diagnose(self.root, self.contract, {'cnpj'})))
        runner.write_text(runner.read_text().replace('def renamed', 'def download'))
        project.write_text('[project.scripts]\nbracc-etl = "bracc_etl.runner:missing"\n')
        self.assertTrue(any('unsupported or missing' in e for e in diagnose(self.root, self.contract, {'cnpj'})))

    def test_cli_doctor_never_runs_commands(self):
        repo = Path(__file__).resolve().parents[3]
        (self.root / 'docs').mkdir()
        (self.root / 'docs/source_registry_br_v1.csv').write_text('pipeline_id,in_universe_v1,implementation_state\nexample,true,implemented\n')
        (self.root / 'config/bootstrap_all_contract.yml').write_text(json.dumps(self.contract))
        result = subprocess.run([sys.executable, str(repo / 'scripts/run_bootstrap_all.py'), '--repo-root', str(self.root), '--doctor', '--yes-reset'], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['config', 'data', 'docs', 'etl'])

    def test_cli_doctor_reports_invalid_command_without_side_effects(self):
        repo = Path(__file__).resolve().parents[3]
        (self.root / 'docs').mkdir()
        (self.root / 'docs/source_registry_br_v1.csv').write_text('pipeline_id,in_universe_v1,implementation_state\nexample,true,implemented\n')
        source = self.contract['sources'][0]
        source['acquisition_mode'] = 'script_download'
        source['download_commands'] = ['python3 /workspace/scripts/missing.py']
        (self.root / 'config/bootstrap_all_contract.yml').write_text(json.dumps(self.contract))
        result = subprocess.run([sys.executable, str(repo / 'scripts/run_bootstrap_all.py'), '--repo-root', str(self.root), '--doctor', '--yes-reset'], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn('unsupported or missing download command', result.stderr)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['config', 'data', 'docs', 'etl'])

    def test_normal_run_validates_bad_command_before_docker(self):
        repo = Path(__file__).resolve().parents[3]
        (self.root / 'docs').mkdir()
        (self.root / 'docs/source_registry_br_v1.csv').write_text('pipeline_id,in_universe_v1,implementation_state\nexample,true,implemented\n')
        source = self.contract['sources'][0]
        source['acquisition_mode'] = 'script_download'
        source['download_commands'] = ['python3 /workspace/scripts/missing.py']
        (self.root / 'config/bootstrap_all_contract.yml').write_text(json.dumps(self.contract))
        empty_path = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: empty_path.rmdir())
        env = {**os.environ, 'PATH': str(empty_path)}
        result = subprocess.run([sys.executable, str(repo / 'scripts/run_bootstrap_all.py'), '--repo-root', str(self.root)], capture_output=True, text=True, check=False, env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn('unsupported or missing download command', result.stderr)
        self.assertNotIn('docker is required', result.stderr)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['config', 'data', 'docs', 'etl'])


if __name__ == '__main__':
    unittest.main()
