FROM python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0

RUN apt-get update \
 && apt-get install -y --no-install-recommends tmux asciinema procps sqlite3 \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir pytest==8.3.4

COPY schemashift/ /opt/schemashift-src/
RUN pip install --no-cache-dir /opt/schemashift-src && rm -rf /opt/schemashift-src

COPY app/ /app/
COPY seed/seed.py /tmp/seed.py
WORKDIR /app
RUN python /tmp/seed.py /app/data/ledger.db /app/migrations 2026 40 \
 && rm /tmp/seed.py /var/log/schemashift.log \
 && find /app -name __pycache__ -prune -exec rm -rf {} +
