import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
WRAPPER = Path(os.environ.get("BOOTSTRAP_WRAPPER_SOURCE", REPO / "scripts/bootstrap_public_demo.sh"))
TIMEOUT = 5
HOSTILE = {"NEO4J_URI": "bolt://hostile", "COMPOSE_PROJECT_NAME": "hostile",
           "DOWNLOAD": "true", "PIPELINES": "all"}


class PublicDemoBootstrapTests(unittest.TestCase):
    def fixture(self, source=WRAPPER):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "scripts").mkdir()
        (root / "infra/scripts").mkdir(parents=True)
        (root / "bin").mkdir()
        (root / "trace").touch()
        wrapper = root / "scripts/bootstrap_public_demo.sh"
        wrapper.write_bytes(source.read_bytes())
        wrapper.chmod(0o755)
        seeder = root / "infra/scripts/seed-dev.sh"
        seeder.write_text("#!/usr/bin/env bash\nprintf 'seeder' >> \"$TRACE\"\nprintf '%s\\n' \"$*|${DEMO_NEO4J_PASSWORD-unset}|${NEO4J_URI-unset}|${COMPOSE_PROJECT_NAME-unset}|${DOWNLOAD-unset}|${PIPELINES-unset}\" >> \"$SEED_ARGS\"\n")
        seeder.chmod(0o755)
        doctor = root / "scripts/run_bootstrap_all.py"
        doctor.write_text("import os, sys\nopen(os.environ['TRACE'], 'a').write('doctor')\nopen(os.environ['DOCTOR_ARGS'], 'w').write(' '.join(sys.argv[1:]))\nsys.exit(int(os.environ.get('DOCTOR_RC', '0')))\n")
        for name in ("docker", "uv", "curl"):
            cmd = root / "bin" / name
            cmd.write_text("#!/usr/bin/env bash\nprintf %s >> \"$TRACE\"\nexit 97\n" % name)
            cmd.chmod(0o755)
        return temp, root, wrapper

    def run_wrapper(self, wrapper, root, *args, env=None):
        clean = {k: v for k, v in os.environ.items() if k not in
                 {"NEO4J_URI", "COMPOSE_PROJECT_NAME", "DOWNLOAD", "PIPELINES", "DEMO_NEO4J_PASSWORD", "PYTHONPATH"}}
        clean.update({"PATH": f"{root / 'bin'}:{clean.get('PATH','')}", "TRACE": str(root/'trace'),
                      "SEED_ARGS": str(root/'seed_args'), "DOCTOR_ARGS": str(root/'doctor_args')})
        clean.update(env or {})
        return subprocess.run(["bash", str(wrapper), *args], cwd=root, env=clean,
                              capture_output=True, text=True, timeout=TIMEOUT, check=False)

    def assert_empty_trace(self, root):
        self.assertEqual((root / "trace").read_text(), "")

    def test_default_help_and_invalid_options_never_dispatch(self):
        cases = [(), ("--help",), ("--profile", "demo"), ("--profile", "full"),
                 ("--profile",), ("--download",), ("--pipelines", "x"), ("--surprise",),
                 ("--doctor", "--reset"), ("--doctor", "--yes-reset"), ("--no-download",),
                 ("--seed-isolated",), ("--seed-isolated", "wrong"),
                 ("--seed-isolated", "--i-understand-isolated-demo", "extra")]
        for args in cases:
            with self.subTest(args=args):
                temp, root, wrapper = self.fixture()
                try:
                    result = self.run_wrapper(wrapper, root, *args, env=HOSTILE)
                    self.assert_empty_trace(root)
                    self.assertEqual(result.returncode, 0 if args in ((), ("--help",)) else 2, result.stderr)
                finally:
                    temp.cleanup()

    def test_doctor_passes_exact_args_and_propagates_exit(self):
        temp, root, wrapper = self.fixture()
        try:
            result = self.run_wrapper(wrapper, root, "--doctor", env={**HOSTILE, "DOCTOR_RC": "7"})
            self.assertEqual((root / "trace").read_text(), "doctor")
            self.assertEqual((root / "doctor_args").read_text(), f"--repo-root {root} --doctor")
            self.assertEqual(result.returncode, 7)
        finally:
            temp.cleanup()

    def test_seed_requires_password_without_dispatch(self):
        temp, root, wrapper = self.fixture()
        try:
            result = self.run_wrapper(wrapper, root, "--seed-isolated", "--i-understand-isolated-demo", env=HOSTILE)
            self.assert_empty_trace(root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("DEMO_NEO4J_PASSWORD", result.stderr)
        finally:
            temp.cleanup()

    def test_seed_dispatches_only_fake_seeder_and_clears_inherited_targets(self):
        temp, root, wrapper = self.fixture()
        try:
            result = self.run_wrapper(wrapper, root, "--seed-isolated", "--i-understand-isolated-demo",
                                      env={**HOSTILE, "DEMO_NEO4J_PASSWORD": "fixture-only"})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / "trace").read_text(), "seeder")
            self.assertEqual((root / "seed_args").read_text().strip(), "|fixture-only|unset|unset|unset|unset")
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
