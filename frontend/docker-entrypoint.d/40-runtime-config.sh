#!/bin/sh
set -eu

config_file="${BRACC_RUNTIME_CONFIG_FILE:-/usr/share/nginx/html/runtime-config.js}"
public_mode="${PUBLIC_MODE:-false}"
patterns_enabled="${PATTERNS_ENABLED:-false}"
api_url="${VITE_API_URL:-}"
app_env="${APP_ENV:-dev}"

case "$public_mode" in
  true|false) ;;
  *) echo "PUBLIC_MODE must be true or false" >&2; exit 1 ;;
esac
case "$patterns_enabled" in
  true|false) ;;
  *) echo "PATTERNS_ENABLED must be true or false" >&2; exit 1 ;;
esac
case "$api_url" in
  *'
'*) echo "VITE_API_URL must be a single-line URL" >&2; exit 1 ;;
esac
if [ -n "$api_url" ] && ! printf '%s' "$api_url" | grep -Eq '^https://[A-Za-z0-9.-]+(:[0-9]{1,5})?$|^http://(localhost|127\.0\.0\.1)(:[0-9]{1,5})?$'; then
  echo "VITE_API_URL must be an HTTPS origin or a local development origin" >&2
  exit 1
fi
if [ "$app_env" = production ] && printf '%s' "$api_url" | grep -Eq '^http://'; then
  echo "VITE_API_URL must use HTTPS in production" >&2
  exit 1
fi

umask 022
cat > "$config_file" <<EOF
window.__BRACC_CONFIG__ = {
  apiBaseUrl: "$api_url",
  publicMode: $public_mode,
  patternsEnabled: $patterns_enabled,
};
EOF
