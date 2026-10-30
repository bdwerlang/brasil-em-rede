#!/bin/sh
set -eu

repo="$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)"
product_context="$repo/infra/postgres"
product_dockerfile="$product_context/Dockerfile"
apk_file="$product_context/su-exec-0.3-r0.apk"
expected='4003163f58cd4a75df79973171d25e4912df4284d8bac9850ac267b58b969be5'
tmp="$(mktemp -d "${TMPDIR:-/tmp}/u03-su-exec-integrity.XXXXXXXX")"
run_id="$(basename "$tmp")"
negative_tag="u03-su-exec-integrity-negative:$run_id"
positive_tag="u03-su-exec-integrity-positive:$run_id"
container_id=''
negative_file="$tmp/Dockerfile"
cleanup() {
    status=$?
    trap - EXIT HUP INT TERM
    if [ -n "$container_id" ]; then docker rm -f "$container_id" >/dev/null 2>&1 || :; fi
    docker image rm "$negative_tag" "$positive_tag" >/dev/null 2>&1 || :
    rm -rf "$tmp"
    exit "$status"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

# Unique mktemp dir above is also the run identity and owned temp namespace.
mkdir -p "$tmp/context"
cp "$product_dockerfile" "$tmp/Dockerfile"
cp "$apk_file" "$tmp/context/su-exec-0.3-r0.apk"
# Keep the original guards, replacing only the expected SHA-256 token.
python3 - "$product_dockerfile" "$negative_file" <<'PY'
import pathlib, sys
src = pathlib.Path(sys.argv[1]).read_text()
token = '4003163f58cd4a75df79973171d25e4912df4284d8bac9850ac267b58b969be5'
assert src.count(token) == 1, 'expected exactly one pinned SHA-256 token'
pathlib.Path(sys.argv[2]).write_text(src.replace(token, '0' * 64, 1))
PY

printf '%s\n' 'RED: exact product Dockerfile rejects only the wrong SHA-256'
if docker build --network=none --build-arg "APK_SHA256=$(printf '%064d' 0)" -f "$negative_file" -t "$negative_tag" "$tmp/context" >"$tmp/negative.log" 2>&1; then
    cat "$tmp/negative.log"
    echo 'ERROR: wrong SHA-256 unexpectedly built' >&2
    exit 1
else
    status=$?
fi
cat "$tmp/negative.log"
grep -Eq 'sha256sum: WARNING: 1 of 1 computed checksums did NOT match|sha256sum: WARNING: 1 computed checksum did NOT match' "$tmp/negative.log"
! grep -q 'fetch .*su-exec\|Installing su-exec' "$tmp/negative.log"
printf 'Negative build exited %s at checksum mismatch before apk add.\n' "$status"

printf '%s\n' 'GREEN: exact product Dockerfile/context builds offline'
docker build --network=none --no-cache -t "$positive_tag" "$product_context"

printf '%s\n' 'SMOKE: su-exec runs postgres identity/version (no DB start)'
container_id="$(docker create --network=none --entrypoint /bin/sh "$positive_tag" -c 'su-exec postgres id; su-exec postgres postgres --version; grep -q "exec su-exec postgres" /usr/local/bin/docker-entrypoint.sh; ! grep -q gosu /usr/local/bin/docker-entrypoint.sh; test ! -e /usr/local/bin/gosu')"
docker start -a "$container_id"
docker rm "$container_id" >/dev/null
container_id=''
