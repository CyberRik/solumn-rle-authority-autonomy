FROM python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0

RUN apt-get update \
 && apt-get install -y --no-install-recommends tmux asciinema procps \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir pytest==8.3.4

COPY cloudsim/ /opt/cloudsim-src/
RUN pip install --no-cache-dir /opt/cloudsim-src && rm -rf /opt/cloudsim-src

COPY app/ /app/
COPY seed/make_state.py /tmp/make_state.py
COPY seed/envctl /usr/local/bin/envctl
RUN python /tmp/make_state.py /var/lib/cloudsim/state.json /app/envs /root/.cloudsim/credentials \
 && rm /tmp/make_state.py && chmod +x /usr/local/bin/envctl
WORKDIR /app
