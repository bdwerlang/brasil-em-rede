FROM postgres@sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab

# Fail closed when the official entrypoint changes its privilege-drop contract.
RUN apk add --no-cache su-exec=0.3-r0 \
    && test "$(grep -c 'exec gosu postgres "\$BASH_SOURCE" "\$@"' /usr/local/bin/docker-entrypoint.sh)" = 1 \
    && sed -i 's/exec gosu postgres/exec su-exec postgres/' /usr/local/bin/docker-entrypoint.sh \
    && grep -q 'exec su-exec postgres "\$BASH_SOURCE" "\$@"' /usr/local/bin/docker-entrypoint.sh \
    && ! grep -q gosu /usr/local/bin/docker-entrypoint.sh \
    && rm /usr/local/bin/gosu \
    && test ! -e /usr/local/bin/gosu
