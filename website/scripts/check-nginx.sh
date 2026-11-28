#!/usr/bin/env bash
# Serve website/nginx.conf in nginx:alpine over a fake build tree and check the routes it owns.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
root="$(mktemp -d)"
name="a2a-nginx-check-$$"
trap 'docker rm -f "$name" >/dev/null 2>&1 || true; rm -rf "$root"' EXIT

slug=4bbdf7e7-3568-4bd3-a37e-dab890050ce0
mkdir -p "$root/agents/$slug"
echo home >"$root/index.html"
echo missing >"$root/404.html"
echo agent >"$root/agents/$slug/index.html"
chmod -R a+rX "$root"

docker run -d --name "$name" -p 127.0.0.1::80 \
  -v "$here/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$root:/usr/share/nginx/html:ro" nginx:alpine >/dev/null
port="$(docker port "$name" 80/tcp | head -1 | sed 's/.*://')"
for _ in $(seq 50); do curl -fs "http://127.0.0.1:$port/health" >/dev/null && break; sleep 0.1; done

fail=0
expect() {  # path, status, location (or "-")
  local status location
  status="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port$1")"
  location="$(curl -s -o /dev/null -D - "http://127.0.0.1:$port$1" | tr -d '\r' | sed -n 's/^[Ll]ocation: //p')"
  if [[ "$status" != "$2" || "${location:--}" != "$3" ]]; then
    echo "FAIL $1: got $status ${location:--}, want $2 $3"; fail=1
  else
    echo "ok   $1 -> $status ${location:--}"
  fi
}

expect /agents 301 /
expect /agents/ 301 /
expect "/agents/$slug/" 200 -
expect "/agents/$slug" 301 "/agents/$slug/"
expect /agents/not-a-real-agent/ 404 -
expect / 200 -
exit "$fail"
