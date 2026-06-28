"""Reference capauth-gate ingress middleware (sketch).

The unified-ingress pattern terminates exactly ONE public :443 hostname and
fans out to localhost/tailnet-only backends. This module is the *edge
enforcement* half: the reverse proxy (Caddy / Traefik / an ASGI app behind
cloudflared) calls into ``gate_decision`` before a request reaches a backend.

Design contract (see UNIFIED_INGRESS_STANDARD.md §"capauth-gate middleware"):

  * **Federation endpoints are public-by-design and PASS THROUGH the gate.**
    ``/api/v1/inbox``, ``/api/v1/prekey`` and ``/.well-known/*`` (DID + SKFed
    descriptors) authenticate at the *envelope* layer — every SKFed envelope is
    PGP/PQC-signed and the backend verifies it with
    ``skcomms.signing.EnvelopeVerifier``. Re-gating them at the edge would break
    peer federation (a peer node holds no edge credential, only a signed
    envelope). The gate therefore *allowlists* the federation prefixes.

  * **Everything else is gated.** A protected app/admin route requires a
    presented CapAuth credential (``Authorization: CapAuth <token>``) that the
    injected ``verify`` callback accepts. In production ``verify`` calls capauth
    (token introspection or a detached-signature check over the request); here
    it is injected so the decision core is unit-testable with no live capauth.

  * **Honest status codes.** 401 = no CapAuth credential presented; 403 = a
    CapAuth credential was presented and rejected. (RFC 7235 semantics.)

This is a *reference sketch*, not a drop-in: wire ``verify`` to your real
capauth verifier and mount ``CapAuthGate`` as ASGI middleware, or call the
``cli`` entry from a Caddy/Traefik ``forward_auth`` / external-auth hop.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

# The federation set that rides the single public :443 funnel. Mirror this list
# verbatim in the Caddyfile / Traefik / cloudflared reference configs so the
# edge and the proxy agree on what is public.
PUBLIC_PREFIXES: tuple[str, ...] = (
    "/.well-known/",        # DID docs + SKFed descriptors (skfed/*)
    "/api/v1/inbox",        # SKFed S2S envelope receive (signed at envelope layer)
    "/api/v1/prekey",       # SKFed PQ prekey fetch/publish
)

# A presented-but-verifiable Verify callback: (token, path) -> accept?
Verify = Callable[[str, str], bool]


@dataclass(frozen=True)
class Decision:
    """The gate's ruling for one request."""

    allowed: bool
    status: int          # 200 allow · 401 no-credential · 403 rejected
    reason: str
    public: bool = False  # True iff matched a public-by-design federation prefix


def _is_public(path: str) -> bool:
    """Anchored prefix match — a public token must START the path.

    ``/app/api/v1/inbox-spoof`` is NOT public; ``/api/v1/inbox`` is.
    """
    return any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES)


def _capauth_token(headers: Mapping[str, str]) -> str | None:
    """Extract a CapAuth bearer token from the Authorization header.

    Header names are matched case-insensitively; the scheme must be ``CapAuth``
    (case-insensitive). Any other scheme (Bearer/Basic) counts as *no CapAuth
    credential presented*.
    """
    auth = None
    for k, v in headers.items():
        if k.lower() == "authorization":
            auth = v
            break
    if not auth:
        return None
    parts = auth.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "capauth":
        return None
    return parts[1].strip() or None


def gate_decision(
    path: str,
    headers: Mapping[str, str],
    verify: Verify,
) -> Decision:
    """Pure gate decision for one request.

    Args:
        path: request path (no query string).
        headers: request headers (any case).
        verify: callback that validates a CapAuth token for ``path``.

    Returns:
        Decision: allow/deny + honest status + whether it was public-by-design.
    """
    if _is_public(path):
        return Decision(True, 200, "federation endpoint (envelope-authenticated)", public=True)

    token = _capauth_token(headers)
    if token is None:
        return Decision(False, 401, "no CapAuth credential presented")

    if not verify(token, path):
        return Decision(False, 403, "CapAuth credential rejected")

    return Decision(True, 200, "CapAuth verified")


# --------------------------------------------------------------------------- #
# ASGI middleware wrapper (sketch) — drives the decision core in production.
# --------------------------------------------------------------------------- #
class CapAuthGate:
    """Minimal ASGI middleware that enforces :func:`gate_decision`.

    Example::

        from skcomms.signing import EnvelopeVerifier  # or capauth token introspect

        def verify(token: str, path: str) -> bool:
            # production: introspect the capauth token, or verify a detached
            # request signature against the caller's pinned capauth pubkey.
            return capauth_introspect(token).get("active", False)

        app = CapAuthGate(asgi_app, verify=verify)
    """

    def __init__(self, app, verify: Verify):
        self.app = app
        self.verify = verify

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "/")
        headers = {
            k.decode("latin1"): v.decode("latin1")
            for k, v in scope.get("headers", [])
        }
        d = gate_decision(path, headers, self.verify)
        if d.allowed:
            await self.app(scope, receive, send)
            return
        body = f'{{"error":"{d.reason}"}}'.encode()
        await send({
            "type": "http.response.start",
            "status": d.status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"www-authenticate", b'CapAuth realm="skfed"'),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})


def cli() -> int:
    """forward_auth helper: read METHOD+PATH+headers from env, exit 0/1.

    Wire as a Caddy/Traefik external-auth hop or a tiny sidecar that returns
    200/401/403. Here it just demonstrates the env contract.
    """
    import json
    import os
    import sys

    path = os.environ.get("REQUEST_PATH", "/")
    headers = json.loads(os.environ.get("REQUEST_HEADERS", "{}"))

    def verify(token: str, _path: str) -> bool:  # demo: env-pinned token
        return token == os.environ.get("CAPAUTH_DEMO_TOKEN", "")

    d = gate_decision(path, headers, verify)
    sys.stderr.write(f"{d.status} {d.reason}\n")
    return 0 if d.allowed else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(cli())
