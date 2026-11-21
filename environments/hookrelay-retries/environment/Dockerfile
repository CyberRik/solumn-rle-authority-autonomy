FROM python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0 AS certs
RUN pip install --no-cache-dir cryptography==43.0.3
COPY certgen/gen_expired.py /gen_expired.py
RUN mkdir /out && python /gen_expired.py /out

FROM python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0

RUN apt-get update \
 && apt-get install -y --no-install-recommends tmux asciinema procps \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir pytest==8.3.4 coverage==7.6.10

COPY app/ /app/
COPY --from=certs /out/server.pem /out/server.key /app/tests/certs/
RUN chmod +x /app/scripts/ci.sh /app/tests/certs/make_certs.sh
WORKDIR /app
