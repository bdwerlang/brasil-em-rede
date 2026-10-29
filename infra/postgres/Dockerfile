FROM postgres@sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab

# Official Alpine v3.24/main x86_64 su-exec 0.3-r0 APK, SHA-256 pinned.
# Fail closed when the official entrypoint changes its privilege-drop contract.
RUN set -eux; \
    test "$(grep -c 'exec gosu postgres "\$BASH_SOURCE" "\$@"' /usr/local/bin/docker-entrypoint.sh)" = 1 \
    && sed -i 's/exec gosu postgres/exec su-exec postgres/' /usr/local/bin/docker-entrypoint.sh \
    && grep -q 'exec su-exec postgres "\$BASH_SOURCE" "\$@"' /usr/local/bin/docker-entrypoint.sh \
    && ! grep -q gosu /usr/local/bin/docker-entrypoint.sh \
    && rm /usr/local/bin/gosu \
    && test ! -e /usr/local/bin/gosu

COPY su-exec-0.3-r0.apk /tmp/su-exec-0.3-r0.apk
RUN set -eux; \
    printf '%s  %s\n' '4003163f58cd4a75df79973171d25e4912df4284d8bac9850ac267b58b969be5' /tmp/su-exec-0.3-r0.apk | sha256sum -c -; \
    apk add --no-cache /tmp/su-exec-0.3-r0.apk; \
    rm -f /tmp/su-exec-0.3-r0.apk
