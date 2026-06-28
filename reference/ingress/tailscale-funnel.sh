#!/usr/bin/env bash
# =============================================================================
# Unified :443 Sovereign Ingress — Tailscale Funnel reference commands
# =============================================================================
# Tailscale Funnel is the SOVEREIGN, ZERO-DEP front door: no Cloudflare, no
# third party in the data path beyond Tailscale's TLS-terminating ingress. It
# exposes a node on the PUBLIC internet at exactly ONE hostname:
#
#       https://<node>.<tailnet>.ts.net           (here: *.tail204f0c.ts.net)
#       e.g. https://noroc2027.tail204f0c.ts.net
#
# THE CORE CONSTRAINT (proven, load-bearing for this whole architecture):
#   Funnel gives you ONE hostname per node and can route ONLY BY PATH. It
#   CANNOT host-route (there is no second public hostname, and no Host-based
#   fan-out). So:
#     * To serve >1 vhost behind Funnel you MUST put a reverse proxy behind it
#       (Caddy/Traefik) and either (a) host-route inside that proxy if the proxy
#       owns real TLS, or (b) accept PATH-based separation.
#     * Federation rides this single public :443: the proven live URL form is
#         https://<node>.tail204f0c.ts.net/api/v1/inbox
#         https://<node>.tail204f0c.ts.net/api/v1/prekey
#
# THE PROVEN --set-path GOTCHA (target path preserved):
#   `tailscale funnel --set-path=/P <target>` mounts a path. The TARGET must
#   carry the path the BACKEND actually routes on, so the path is PRESERVED
#   end-to-end to the backend. We mount each federation path at its FULL target
#   path (…/api/v1/inbox -> …:8765/api/v1/inbox) rather than mounting "/" and
#   hoping the prefix survives. This is the configuration that works here.
#   Mounting at "/" forwards everything to one backend (fine if a reverse proxy
#   is that backend and does its own routing — OPTION B below).
#
# Requires: Funnel enabled in the tailnet ACL policy + node tagged/allowed for
# Funnel (`tailscale set --advertise-... ` / admin console Funnel grant).
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# OPTION A — direct path-mounts to backends (no reverse proxy).
# Each federation endpoint is mounted at its FULL target path so the backend
# (skcomms API on 127.0.0.1:8765) receives the path it routes on. Good when one
# backend owns all the public paths.
# ---------------------------------------------------------------------------
tailscale funnel --bg --set-path=/api/v1/inbox   http://127.0.0.1:8765/api/v1/inbox
tailscale funnel --bg --set-path=/api/v1/prekey  http://127.0.0.1:8765/api/v1/prekey
# /.well-known/ covers both DID (/.well-known/did.json) and SKFed descriptors
# (/.well-known/skfed/*). Mount the prefix at its full target path:
tailscale funnel --bg --set-path=/.well-known    http://127.0.0.1:8765/.well-known

# Inspect what is published:
tailscale funnel status

# ---------------------------------------------------------------------------
# OPTION B — Funnel -> ONE reverse proxy, which does host/path/middleware.
# This is the recommended unified-ingress shape: Funnel mounts "/" onto a local
# Caddy/Traefik, and the proxy owns the SKFed routes + the capauth-gate + any
# vhosting. Funnel stays a dumb single-hostname transport; routing is sovereign
# and in-repo (Caddyfile / traefik-dynamic.yml).
# ---------------------------------------------------------------------------
# tailscale funnel --bg http://127.0.0.1:8080     # Caddy/Traefik plaintext entrypoint
# tailscale funnel status

# ---------------------------------------------------------------------------
# Tear down:
#   tailscale funnel reset
# ---------------------------------------------------------------------------
