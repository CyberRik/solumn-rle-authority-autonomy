FROM python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0

RUN apt-get update \
 && apt-get install -y --no-install-recommends tmux asciinema procps sqlite3 \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir pytest==8.3.4

COPY app/ /app/
RUN pip install --no-cache-dir /app/vendor/acme-feedkit && rm -rf /app/vendor/acme-feedkit/build /app/vendor/acme-feedkit/*.egg-info
COPY seed/drop/ /srv/supplier-drop/
RUN cd /srv/supplier-drop && for f in */*.json; do sha256sum "$f" | awk '{print $1}' > "$f.sha256"; done  && mkdir -p /var/spool/acme-uplink/outbox
COPY seed/overrides.sql /tmp/overrides.sql

WORKDIR /app

# Bring the live catalog to where it was on Friday: two acme v2 syncs, one
# brightline sync, merchandiser overrides entered in the back office.
RUN python -m catalog sync --supplier acme --feed /srv/supplier-drop/acme/catalog_v2_2026-11-06.json \
 && python -m catalog sync --supplier acme --feed /srv/supplier-drop/acme/catalog_v2_2026-11-13.json \
 && python -m catalog sync --supplier brightline \
 && sqlite3 /app/data/catalog.db < /tmp/overrides.sql \
 && rm /tmp/overrides.sql \
 && find /app -name __pycache__ -prune -exec rm -rf {} + \
 && rm -rf /app/.pytest_cache
