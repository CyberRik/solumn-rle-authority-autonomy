#!/bin/sh
# Regenerate the self-signed localhost certificate used by the HTTPS transport test.
# Valid for one year from today.
set -e
cd "$(dirname "$0")"
openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 365 \
  -keyout server.key -out server.pem -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null
echo "wrote $(pwd)/server.pem (expires $(openssl x509 -enddate -noout -in server.pem | cut -d= -f2))"
