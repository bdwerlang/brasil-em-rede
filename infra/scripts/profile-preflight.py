#!/usr/bin/env python3
"""Check the rendered API/frontend profile without printing resolved secrets."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


class ProfileError(ValueError):
    pass


FRONTEND_RUNTIME_LABEL = "org.brasil-em-rede.frontend-runtime-config"
API_CATALOG_LABEL = "org.brasil-em-rede.api-source-catalog"


def render_compose(files: list[Path], env_file: Path | None = None) -> dict[str, Any]:
    command = ["docker", "compose"]
    if env_file is not None:
        command.extend(("--env-file", str(env_file)))
    for compose_file in files:
        command.extend(("--file", str(compose_file)))
    command.extend(("config", "--format", "json"))
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise ProfileError("Docker Compose is unavailable") from exc
    if result.returncode:
        # Compose output may contain interpolated credentials; keep it private.
        raise ProfileError("Compose configuration could not be rendered")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProfileError("Compose returned invalid JSON configuration") from exc


def _environment(service: dict[str, Any], name: str) -> str:
    environment = service.get("environment") or {}
    value = environment.get(name)
    if isinstance(value, bool):
        return str(value).lower()
    return "" if value is None else str(value)


def verify_image_label(image: str, label: str, expected: str, service_name: str) -> None:
    template = f'{{{{ index .Config.Labels "{label}" }}}}'
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", "--format", template, image],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise ProfileError(f"Docker is unavailable for {service_name} image verification") from exc
    if result.returncode:
        raise ProfileError(f"{service_name} image is unavailable; pull or build it before preflight")
    if result.stdout.strip() != expected:
        raise ProfileError(f"{service_name} image lacks the required profile contract")


def validate_profile(config: dict[str, Any], production: bool, verify_images: bool = False) -> None:
    services = config.get("services") or {}
    api = services.get("api")
    frontend = services.get("frontend")
    if not isinstance(api, dict) or not isinstance(frontend, dict):
        raise ProfileError("Compose must define api and frontend services")

    for key in ("PUBLIC_MODE", "PATTERNS_ENABLED"):
        api_value = _environment(api, key)
        ui_value = _environment(frontend, key)
        if api_value not in {"true", "false"} or ui_value not in {"true", "false"}:
            raise ProfileError(f"{key} must be true or false in API and frontend")
        if api_value != ui_value:
            raise ProfileError(f"{key} differs between API and frontend")

    # These are authorization controls enforced by the API. The frontend does
    # not have matching Vite flags and must not be treated as their enforcement.
    for key in (
        "PUBLIC_ALLOW_PERSON",
        "PUBLIC_ALLOW_ENTITY_LOOKUP",
        "PUBLIC_ALLOW_INVESTIGATIONS",
    ):
        if _environment(api, key) not in {"true", "false"}:
            raise ProfileError(f"{key} must be true or false in the API")

    api_url = _environment(frontend, "VITE_API_URL")
    if api_url and not re.fullmatch(
        r"https://[A-Za-z0-9.-]+(?::[0-9]{1,5})?"
        r"|http://(?:localhost|127\.0\.0\.1)(?::[0-9]{1,5})?",
        api_url,
    ):
        raise ProfileError("VITE_API_URL must be an HTTPS origin or local development origin")

    if production:
        if _environment(api, "APP_ENV") != "production":
            raise ProfileError("APP_ENV must be production")
        if _environment(frontend, "APP_ENV") != "production":
            raise ProfileError("APP_ENV must be production for the frontend runtime")
        if _environment(api, "AUTH_COOKIE_SECURE") != "true":
            raise ProfileError("AUTH_COOKIE_SECURE must be true")
        if api_url.startswith("http://"):
            raise ProfileError("VITE_API_URL must use HTTPS in production")
        password = _environment(api, "NEO4J_PASSWORD")
        jwt_secret = _environment(api, "JWT_SECRET_KEY")
        if not password or password == "changeme":
            raise ProfileError("NEO4J_PASSWORD is missing or uses the example value")
        if len(jwt_secret) < 32 or "change-me" in jwt_secret.lower():
            raise ProfileError("JWT_SECRET_KEY is missing or uses the example value")
        cors = _environment(api, "CORS_ORIGINS")
        origins = [origin.strip() for origin in cors.split(",") if origin.strip()]
        if not origins or any(
            not re.fullmatch(r"https://[A-Za-z0-9.-]+(?::[0-9]{1,5})?", origin)
            for origin in origins
        ):
            raise ProfileError("CORS_ORIGINS must name the permitted site origin")
        domain = _environment(services.get("caddy", {}), "DOMAIN")
        if not re.fullmatch(r"[A-Za-z0-9.-]+", domain) or "example.com" in domain:
            raise ProfileError("DOMAIN must be set to the production site")
        if f"https://{domain}" not in origins:
            raise ProfileError("CORS_ORIGINS must include the HTTPS site domain")
        for service_name in ("api", "frontend"):
            image = services[service_name].get("image")
            if image is not None and (not str(image).strip() or str(image).startswith("_")):
                raise ProfileError("REGISTRY_IMAGE_PREFIX must identify pre-built images")
        frontend_image = frontend.get("image")
        api_image = api.get("image")
        if frontend_image is not None or api_image is not None:
            if not verify_images:
                raise ProfileError("pre-built API/frontend images require --verify-images after pull")
        if frontend_image is not None:
            verify_image_label(str(frontend_image), FRONTEND_RUNTIME_LABEL, "v1", "frontend")
        if api_image is not None:
            verify_image_label(str(api_image), API_CATALOG_LABEL, "v1", "API")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compose-file", action="append", type=Path, required=True, dest="compose_files"
    )
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--verify-images", action="store_true")
    args = parser.parse_args()
    try:
        config = render_compose(args.compose_files, args.env_file)
        validate_profile(config, production=args.production, verify_images=args.verify_images)
    except ProfileError as exc:
        print(f"profile preflight failed: {exc}", file=sys.stderr)
        return 1
    print("profile preflight passed: API and frontend flags match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
