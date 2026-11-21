FROM python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0

RUN apt-get update \
 && apt-get install -y --no-install-recommends tmux asciinema procps \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir pytest==8.3.4

COPY coldstore/ /opt/coldstore-src/
RUN pip install --no-cache-dir /opt/coldstore-src && rm -rf /opt/coldstore-src

COPY seed/gen_shards.py /tmp/gen_shards.py
RUN python /tmp/gen_shards.py /srv/archive/events/2026-10 24 2500 2026 && rm /tmp/gen_shards.py \
 && mkdir -p /var/log/coldstore

COPY app/ /app/
WORKDIR /app
