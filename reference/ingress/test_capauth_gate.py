"""Tests for the reference capauth-gate ingress middleware.

Run from anywhere:  pytest reference/ingress/test_capauth_gate.py -q

These tests pin the *gate decision* — the pure, framework-agnostic core that an
ASGI/Starlette/Caddy-exec wrapper drives. The decision must:

  1. PASS THROUGH public-by-design federation endpoints unconditionally. These
     ride the single public :443 funnel and are authenticated at the *envelope*
     layer (capauth ``EnvelopeSigner`` signatures verified by the backend), NOT
     at the ingress. Gating them at the edge would break federation.
  2. GATE everything else: a protected app/admin route needs a presented
     CapAuth credential that the injected ``verify`` callback accepts.
  3. Deny with the right status: 401 when no credential is presented, 403 when a
     credential is presented but rejected.
"""

from __future__ import annotations

import pytest

from capauth_gate import Decision, PUBLIC_PREFIXES, gate_decision


# --- a stub verifier: accepts exactly one good token --------------------------

def make_verify(good="GOODSIG"):
    def verify(token: str, path: str) -> bool:
        return token == good
    return verify


# --- public-by-design federation endpoints PASS THROUGH (no credential) -------

@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/inbox",
        "/api/v1/prekey",
        "/.well-known/did.json",
        "/.well-known/skfed/descriptor.json",
        "/.well-known/skfed/anything/deeper",
    ],
)
def test_federation_endpoints_pass_through_without_credential(path):
    d = gate_decision(path, headers={}, verify=make_verify())
    assert isinstance(d, Decision)
    assert d.allowed is True
    assert d.status == 200
    assert d.public is True  # flagged as envelope-authenticated, not edge-gated


def test_public_prefixes_advertised():
    # The federation set must be declared so configs can mirror it verbatim.
    for p in ("/.well-known/", "/api/v1/inbox", "/api/v1/prekey"):
        assert p in PUBLIC_PREFIXES


# --- protected routes REQUIRE a valid CapAuth credential ----------------------

def test_protected_route_allows_valid_capauth():
    d = gate_decision(
        "/admin/deploy",
        headers={"authorization": "CapAuth GOODSIG"},
        verify=make_verify(),
    )
    assert d.allowed is True
    assert d.status == 200
    assert d.public is False


def test_protected_route_missing_credential_is_401():
    d = gate_decision("/admin/deploy", headers={}, verify=make_verify())
    assert d.allowed is False
    assert d.status == 401


def test_protected_route_bad_credential_is_403():
    d = gate_decision(
        "/admin/deploy",
        headers={"authorization": "CapAuth WRONG"},
        verify=make_verify(),
    )
    assert d.allowed is False
    assert d.status == 403


def test_header_scheme_is_case_insensitive():
    d = gate_decision(
        "/admin/deploy",
        headers={"Authorization": "capauth GOODSIG"},
        verify=make_verify(),
    )
    assert d.allowed is True


def test_non_capauth_scheme_is_401_not_403():
    # A Bearer/Basic token is "no CapAuth credential presented" -> 401.
    d = gate_decision(
        "/admin/deploy",
        headers={"authorization": "Bearer xyz"},
        verify=make_verify(),
    )
    assert d.allowed is False
    assert d.status == 401


def test_public_prefix_match_is_anchored_not_substring():
    # A path that merely CONTAINS a public token but is not under it must gate.
    d = gate_decision("/app/api/v1/inbox-spoof", headers={}, verify=make_verify())
    assert d.allowed is False
    assert d.status == 401
