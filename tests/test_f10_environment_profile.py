import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_CONFIG = ROOT / "frontend/docker-entrypoint.d/40-runtime-config.sh"
spec = importlib.util.spec_from_file_location(
    "f10_profile_preflight", ROOT / "infra/scripts/profile-preflight.py"
)
preflight = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(preflight)


def compose_config(*, patterns="true", ui_patterns=None, app_env="production"):
    ui_patterns = patterns if ui_patterns is None else ui_patterns
    return {
        "services": {
            "api": {
                "environment": {
                    "APP_ENV": app_env,
                    "PUBLIC_MODE": "true",
                    "PATTERNS_ENABLED": patterns,
                    "PUBLIC_ALLOW_PERSON": "false",
                    "PUBLIC_ALLOW_ENTITY_LOOKUP": "false",
                    "PUBLIC_ALLOW_INVESTIGATIONS": "false",
                    "AUTH_COOKIE_SECURE": "true",
                    "NEO4J_PASSWORD": "synthetic-neo4j-password",
                    "JWT_SECRET_KEY": "synthetic-jwt-secret-key-with-more-than-32-characters",
                    "CORS_ORIGINS": "https://demo.invalid",
                }
            },
            "frontend": {
                "environment": {
                    "APP_ENV": app_env,
                    "PUBLIC_MODE": "true",
                    "PATTERNS_ENABLED": ui_patterns,
                    "VITE_API_URL": "",
                }
            },
            "caddy": {"environment": {"DOMAIN": "demo.invalid"}},
        }
    }


class TestF10EnvironmentProfile(unittest.TestCase):
    def test_runtime_config_writes_flags_and_same_origin_api(self):
        with tempfile.TemporaryDirectory() as temporary:
            config_file = Path(temporary) / "runtime-config.js"
            result = subprocess.run(
                ["sh", str(FRONTEND_CONFIG)],
                env={
                    **os.environ,
                    "BRACC_RUNTIME_CONFIG_FILE": str(config_file),
                    "PUBLIC_MODE": "true",
                    "PATTERNS_ENABLED": "false",
                    "VITE_API_URL": "",
                    "APP_ENV": "production",
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = config_file.read_text()
            self.assertIn('apiBaseUrl: ""', config)
            self.assertIn("publicMode: true", config)
            self.assertIn("patternsEnabled: false", config)

    def test_runtime_config_rejects_injected_api_url(self):
        for api_url in (
            'https://safe.invalid";alert(1);//',
            "https://safe.invalid\nalert(1)//",
        ):
            with self.subTest(api_url=api_url), tempfile.TemporaryDirectory() as temporary:
                config_file = Path(temporary) / "runtime-config.js"
                result = subprocess.run(
                    ["sh", str(FRONTEND_CONFIG)],
                    env={
                        **os.environ,
                        "BRACC_RUNTIME_CONFIG_FILE": str(config_file),
                        "PUBLIC_MODE": "false",
                        "PATTERNS_ENABLED": "false",
                        "VITE_API_URL": api_url,
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("alert(1)", result.stderr)
                self.assertFalse(config_file.exists())

    def test_preflight_accepts_matching_production_profile(self):
        preflight.validate_profile(compose_config(), production=True)

    def test_preflight_rejects_flag_divergence_and_example_secrets(self):
        with self.assertRaisesRegex(preflight.ProfileError, "differs"):
            preflight.validate_profile(compose_config(ui_patterns="false"), production=True)
        config = compose_config()
        config["services"]["api"]["environment"]["NEO4J_PASSWORD"] = "changeme"
        with self.assertRaisesRegex(preflight.ProfileError, "NEO4J_PASSWORD"):
            preflight.validate_profile(config, production=True)

    def test_preflight_rejects_public_placeholders(self):
        config = compose_config()
        config["services"]["caddy"]["environment"]["DOMAIN"] = "bracc.example.com"
        with self.assertRaisesRegex(preflight.ProfileError, "DOMAIN"):
            preflight.validate_profile(config, production=True)
        config = compose_config()
        config["services"]["api"]["environment"]["CORS_ORIGINS"] = "https://other.invalid"
        with self.assertRaisesRegex(preflight.ProfileError, "CORS_ORIGINS"):
            preflight.validate_profile(config, production=True)

    def test_preflight_requires_api_authorization_flags(self):
        config = compose_config()
        del config["services"]["api"]["environment"]["PUBLIC_ALLOW_PERSON"]
        with self.assertRaisesRegex(preflight.ProfileError, "PUBLIC_ALLOW_PERSON"):
            preflight.validate_profile(config, production=True)

    def test_preflight_rejects_prebuilt_frontend_without_runtime_label(self):
        config = compose_config()
        config["services"]["frontend"]["image"] = "ghcr.io/example/bracc_frontend:old"
        with self.assertRaisesRegex(preflight.ProfileError, "--verify-images"):
            preflight.validate_profile(config, production=True)
        with patch.object(
            preflight.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, "<no value>\n", ""),
        ):
            with self.assertRaisesRegex(preflight.ProfileError, "required profile contract"):
                preflight.validate_profile(config, production=True, verify_images=True)
        with patch.object(
            preflight.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, "v1\n", ""),
        ):
            preflight.validate_profile(config, production=True, verify_images=True)

    def test_preflight_rejects_prebuilt_api_without_catalog_label(self):
        config = compose_config()
        config["services"]["api"]["image"] = "ghcr.io/example/bracc_api:old"
        config["services"]["frontend"]["image"] = "ghcr.io/example/bracc_frontend:old"
        with patch.object(
            preflight.subprocess,
            "run",
            side_effect=[
                subprocess.CompletedProcess([], 0, "v1\n", ""),
                subprocess.CompletedProcess([], 0, "<no value>\n", ""),
            ],
        ):
            with self.assertRaisesRegex(preflight.ProfileError, "API image lacks"):
                preflight.validate_profile(config, production=True, verify_images=True)

    def test_runtime_config_loads_before_application_bundle(self):
        html = (ROOT / "frontend/index.html").read_text()
        self.assertLess(
            html.index('<script src="/runtime-config.js"></script>'),
            html.index('<script type="module" src="/src/main.tsx"></script>'),
        )
        nginx = (ROOT / "frontend/nginx.conf").read_text()
        self.assertIn('add_header Cache-Control "no-store, no-cache, must-revalidate";', nginx)


if __name__ == "__main__":
    unittest.main()
