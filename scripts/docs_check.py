#!/usr/bin/env python3
"""Docs freshness validator (DOCS_FRESHNESS_STANDARD).

Three tiers, in increasing order of value:

  1. presence   - the 7 files SK_REPO_DOC_STANDARD requires exist.
  2. changelog  - a PR touching src/** or pyproject.toml also touches CHANGELOG.md.
  3. evidence   - every check in SOP.md's `docs-evidence` block still exits 0,
                  and public API/configuration/SIEM claim inventories match their
                  declared source symbols exactly.

Tier 3 is the one that catches drift. Tiers 1 and 2 catch a MISSING doc; tier 3
catches a doc that is present, confident, and WRONG, which is the case that hurts
because it is trusted. A doc nothing executes rots silently.

Usage:
  docs_check.py [--repo PATH] [--tier 1|2|3] [--base-ref REF] [--changed-files FILE]
  docs_check.py --self-test        # negative control: prove the checks can FAIL

Exit 0 = all selected tiers pass, 1 = at least one failure.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED = ["README.md", "SOP.md", "SECURITY.md", "CONTRIBUTING.md",
            "CODE_OF_CONDUCT.md", "CHANGELOG.md", "LICENSE"]
CODE_GLOBS = ("src/", "pyproject.toml")
EVIDENCE_RE = re.compile(r"<!--\s*docs-evidence(.*?)-->", re.S)
MIN_CHECKS = 3
PUBLIC_CLAIMS_MANIFEST = Path("docs/source-evidence.json")
PUBLIC_CLAIM_DOCS = {
    "api_routes": Path("docs/API.md"),
    "configuration_keys": Path("docs/CONFIGURATION.md"),
    "siem_event_types": Path("docs/SIEM.md"),
}
CLAIM_KINDS = frozenset(PUBLIC_CLAIM_DOCS)

OK, BAD = "  ok   ", "  FAIL "


def _fail(msg: str) -> bool:
    print(f"{BAD}{msg}")
    return False


def _ok(msg: str) -> bool:
    print(f"{OK}{msg}")
    return True


# ---------------------------------------------------------------- tier 1
def tier1_presence(repo: Path) -> bool:
    good = True
    missing = [f for f in REQUIRED if not (repo / f).exists()]
    for f in REQUIRED:
        if f in missing:
            good = _fail(f"missing required doc: {f}")
    if good:
        _ok(f"all {len(REQUIRED)} required docs present")
    return good


# ---------------------------------------------------------------- tier 2
def tier2_changelog(repo: Path, changed: list[str] | None) -> bool:
    if changed is None:
        return _ok("changelog check skipped (no diff context; not a PR)")
    touches_code = any(c.startswith(CODE_GLOBS) for c in changed)
    if not touches_code:
        return _ok("changelog check n/a (no code touched)")
    if any(c == "CHANGELOG.md" for c in changed):
        return _ok("code changed and CHANGELOG.md updated")
    return _fail("code under src/ or pyproject.toml changed but CHANGELOG.md did not. "
                 "Add an entry, or use the docs-exempt label / [skip-changelog] for a "
                 "genuinely trivial change.")


# ---------------------------------------------------------------- tier 3

def _repo_path(repo: Path, value: object, field: str) -> tuple[Path | None, str | None]:
    """Resolve a manifest path without allowing it to escape the repository."""
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None, f"{field} must be a non-empty repository-relative path"
    resolved = (repo / value).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError:
        return None, f"{field} escapes the repository: {value}"
    return resolved, None


def _claim_block(text: str, kind: str) -> tuple[str | None, str | None]:
    start = f"<!-- docs-claims:{kind} -->"
    end = f"<!-- /docs-claims:{kind} -->"
    start_count, end_count = text.count(start), text.count(end)
    if start_count != 1 or end_count != 1:
        return None, (f"expected exactly one {start!r} and one {end!r}; "
                      f"found {start_count} and {end_count}")
    before, rest = text.split(start, 1)
    body, after = rest.split(end, 1)
    if end in before or start in after:
        return None, f"malformed or nested docs claim block for {kind}"
    return body, None


def _doc_claims(text: str, kind: str) -> tuple[list[str], str | None]:
    body, err = _claim_block(text, kind)
    if err:
        return [], err
    assert body is not None
    if kind == "api_routes":
        claims = re.findall(
            r"(?m)^\s*(?:[-*]\s+)?`?((?:GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS)\s+/[^`\s]*)`?\s*$",
            body,
        )
        claims = [re.sub(r"\s+", " ", claim.strip()) for claim in claims]
    else:
        claims = re.findall(r"(?m)^\s*[-*]\s+`([^`]+)`\s*$", body)
        claims = [claim.strip() for claim in claims]
    if not claims:
        return [], f"{kind} claim block contains no recognized claims"
    duplicates = sorted({claim for claim in claims if claims.count(claim) > 1})
    if duplicates:
        return [], f"{kind} claim block contains duplicate claims: {', '.join(duplicates)}"
    return claims, None


def _balanced_js_literal(text: str, start: int, opener: str, closer: str) -> tuple[str | None, str | None]:
    """Return one balanced JS array/object while ignoring delimiters in strings/comments."""
    depth, quote, escaped, line_comment, block_comment = 0, None, False, False, False
    i = start
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if line_comment:
            if ch == "\n":
                line_comment = False
        elif block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                i += 1
        elif quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in "'\"`":
            quote = ch
        elif ch == "/" and nxt == "/":
            line_comment = True
            i += 1
        elif ch == "/" and nxt == "*":
            block_comment = True
            i += 1
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start:i + 1], None
        i += 1
    return None, f"unterminated {opener}{closer} literal"


def _without_js_comments(literal: str) -> str:
    """Blank JS comments while preserving strings and character positions."""
    out = list(literal)
    quote, escaped, line_comment, block_comment = None, False, False, False
    i = 0
    while i < len(literal):
        ch = literal[i]
        nxt = literal[i + 1] if i + 1 < len(literal) else ""
        if line_comment:
            if ch == "\n":
                line_comment = False
            else:
                out[i] = " "
        elif block_comment:
            out[i] = " "
            if ch == "*" and nxt == "/":
                out[i + 1] = " "
                block_comment = False
                i += 1
        elif quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in "'\"`":
            quote = ch
        elif ch == "/" and nxt == "/":
            out[i] = out[i + 1] = " "
            line_comment = True
            i += 1
        elif ch == "/" and nxt == "*":
            out[i] = out[i + 1] = " "
            block_comment = True
            i += 1
        i += 1
    return "".join(out)


def _js_strings(literal: str) -> tuple[list[str], str | None]:
    """Extract simple claim strings; inventories deliberately forbid escapes."""
    literal = _without_js_comments(literal)
    values = []
    for match in re.finditer(r"(['\"`])((?:\\.|[^'\"`\n])*)\1", literal):
        if "\\" in match.group(2):
            return [], "claim inventories must use literal strings without escapes"
        values.append(match.group(2))
    return values, None


def _source_claims(text: str, symbol: object, shape: object) -> tuple[list[str], str | None]:
    if not isinstance(symbol, str) or not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", symbol):
        return [], "source_symbol must be a JavaScript identifier"
    if shape not in {"array", "object_values"}:
        return [], "source_shape must be 'array' or 'object_values'"
    matches = list(re.finditer(
        rf"(?:export\s+)?const\s+{re.escape(symbol)}\s*=",
        text,
    ))
    if len(matches) != 1:
        return [], f"expected exactly one const {symbol} assignment; found {len(matches)}"
    opener, closer = ("[", "]") if shape == "array" else ("{", "}")
    initializer = text[matches[0].end():]
    if shape == "array":
        prefix = re.match(r"\s*\[", initializer)
    else:
        prefix = re.match(r"\s*(?:Object\.freeze\s*\(\s*)?\{", initializer)
    if prefix is None:
        return [], f"const {symbol} must be a direct {opener}{closer} literal"
    start = matches[0].end() + prefix.end() - 1
    literal, err = _balanced_js_literal(text, start, opener, closer)
    if err:
        return [], err
    assert literal is not None
    if shape == "array":
        values, err = _js_strings(literal)
    else:
        literal = _without_js_comments(literal)
        values = []
        cursor = 1
        entry_re = re.compile(
            r"\s*(?:[A-Za-z_$][A-Za-z0-9_$]*|(['\"`])([^'\"`\\\n]+)\1)\s*:\s*"
            r"(['\"`])([^'\"`\\\n]*)\3\s*(?:,|$)"
        )
        body = literal[1:-1]
        cursor = 0
        while cursor < len(body):
            if not body[cursor:].strip():
                break
            match = entry_re.match(body, cursor)
            if match is None:
                return [], f"const {symbol} must contain only literal string-valued entries"
            values.append(match.group(4))
            cursor = match.end()
        err = None
    if err:
        return [], err
    if not values:
        return [], f"const {symbol} contains no string claims"
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        return [], f"const {symbol} contains duplicate claims: {', '.join(duplicates)}"
    return values, None


def _validate_claim_syntax(kind: str, claims: list[str]) -> str | None:
    patterns = {
        "api_routes": r"(?:GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS) /\S+",
        "configuration_keys": r"[a-z][a-z0-9_]*(?:\.(?:[a-z][a-z0-9_]*|<[^>]+>))*",
        "siem_event_types": r"[a-z][a-z0-9_]*",
    }
    invalid = [claim for claim in claims if not re.fullmatch(patterns[kind], claim)]
    if invalid:
        return f"invalid {kind} claim syntax: {', '.join(invalid)}"
    return None


def tier3_public_claims(repo: Path) -> bool:
    """Bind conventional public-doc inventories to explicit source symbols.

    This proves inventory equality only. It deliberately does not execute handlers,
    validate config semantics/default values, or prove that an event reaches a sink.
    """
    manifest_path = repo / PUBLIC_CLAIMS_MANIFEST
    present_docs = [str(path) for path in PUBLIC_CLAIM_DOCS.values() if (repo / path).exists()]
    if not manifest_path.exists():
        if present_docs:
            return _fail(
                f"public claim docs exist ({', '.join(present_docs)}) but "
                f"{PUBLIC_CLAIMS_MANIFEST} is missing; tier 3 cannot certify them"
            )
        return _ok("public API/configuration/SIEM claims n/a (no conventional public claim docs)")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return _fail(f"cannot parse {PUBLIC_CLAIMS_MANIFEST}: {exc}")
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        return _fail(f"{PUBLIC_CLAIMS_MANIFEST} must be an object with version 1")
    bindings = manifest.get("bindings")
    if not isinstance(bindings, list):
        return _fail(f"{PUBLIC_CLAIMS_MANIFEST} bindings must be a list")
    by_kind: dict[str, dict] = {}
    for binding in bindings:
        if not isinstance(binding, dict) or binding.get("kind") not in CLAIM_KINDS:
            return _fail(f"{PUBLIC_CLAIMS_MANIFEST} has an invalid claim binding")
        kind = binding["kind"]
        if kind in by_kind:
            return _fail(f"{PUBLIC_CLAIMS_MANIFEST} repeats binding kind {kind}")
        by_kind[kind] = binding
    if set(by_kind) != CLAIM_KINDS:
        missing = sorted(CLAIM_KINDS - set(by_kind))
        extra = sorted(set(by_kind) - CLAIM_KINDS)
        return _fail(f"public claim bindings must be exactly {sorted(CLAIM_KINDS)}; "
                     f"missing={missing}, extra={extra}")

    good = True
    for kind in sorted(CLAIM_KINDS):
        binding = by_kind[kind]
        expected_doc = str(PUBLIC_CLAIM_DOCS[kind])
        if binding.get("document") != expected_doc:
            good = _fail(f"{kind}.document must be {expected_doc}") and good
            continue
        doc_path, err = _repo_path(repo, binding.get("document"), f"{kind}.document")
        if err:
            good = _fail(err) and good
            continue
        source_path, err = _repo_path(repo, binding.get("source"), f"{kind}.source")
        if err:
            good = _fail(err) and good
            continue
        assert doc_path is not None and source_path is not None
        try:
            doc_text = doc_path.read_text(encoding="utf-8")
            source_text = source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            good = _fail(f"cannot read {kind} binding: {exc}") and good
            continue
        documented, err = _doc_claims(doc_text, kind)
        if err:
            good = _fail(f"{binding['document']}: {err}") and good
            continue
        sourced, err = _source_claims(
            source_text,
            binding.get("source_symbol"),
            binding.get("source_shape"),
        )
        if err:
            good = _fail(f"{binding['source']}: {err}") and good
            continue
        err = _validate_claim_syntax(kind, documented) or _validate_claim_syntax(kind, sourced)
        if err:
            good = _fail(err) and good
            continue
        doc_set, source_set = set(documented), set(sourced)
        if doc_set != source_set:
            missing = sorted(source_set - doc_set)
            invented = sorted(doc_set - source_set)
            good = _fail(f"{kind} drift: missing_from_docs={missing}, "
                         f"not_in_source={invented}") and good
        else:
            _ok(f"{kind}: {len(doc_set)} documented claims match {binding['source']}::{binding['source_symbol']}")
    if good:
        _ok("public-doc certification scope: exact route/key/event inventory equality only; "
            "not handler reachability, config semantics/defaults, event delivery, prose outside marked blocks, or live state")
    return good


def parse_evidence(sop: Path) -> tuple[str | None, list[dict], str | None]:
    """Return (verified_date, checks, error). Hand-rolled: the block is a tiny,
    fixed shape, and requiring PyYAML would make the gate fail for the wrong
    reason on a minimal runner."""
    if not sop.exists():
        return None, [], "SOP.md not found"
    m = EVIDENCE_RE.search(sop.read_text(encoding="utf-8", errors="replace"))
    if not m:
        return None, [], "SOP.md has no <!-- docs-evidence --> block"
    verified, checks, cur = None, [], None
    for raw in m.group(1).splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if re.match(r"\s*verified:", line):
            verified = line.split(":", 1)[1].strip()
        elif re.match(r"\s*-\s+name:", line):
            cur = {"name": line.split("name:", 1)[1].strip(), "run": None}
            checks.append(cur)
        elif re.match(r"\s*run:", line) and cur is not None:
            cur["run"] = line.split("run:", 1)[1].strip()
    return verified, [c for c in checks if c.get("run")], None


def tier3_evidence(repo: Path) -> bool:
    public_claims_good = tier3_public_claims(repo)
    verified, checks, err = parse_evidence(repo / "SOP.md")
    if err:
        _fail(err)
        return False
    if len(checks) < MIN_CHECKS:
        _fail(f"docs-evidence has {len(checks)} check(s); the standard requires "
              f">= {MIN_CHECKS}. Cover the facts most likely to drift: entry "
              f"points, ports, unit names, config paths.")
        return False
    good = public_claims_good
    if not verified:
        good = _fail("docs-evidence has no `verified:` date")
    else:
        _ok(f"SOP last verified: {verified}")
    for c in checks:
        r = subprocess.run(["bash", "-lc", c["run"]], cwd=repo,
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            _ok(f"{c['name']}")
        else:
            good = _fail(f"{c['name']}  ->  `{c['run']}` exited {r.returncode}. "
                         f"The SOP documents something that is no longer true.")
            tail = (r.stderr or r.stdout or "").strip().splitlines()[-2:]
            for t in tail:
                print(f"         {t[:120]}")
    return good


# ---------------------------------------------------------------- negative control
def self_test() -> bool:
    """Prove the checks can FAIL. A gate that passes everything is worth no more
    than one that never ran, so this is not optional ceremony."""
    print("negative control: building a repo that SHOULD fail every tier")
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / "README.md").write_text("x")          # 6 of 7 required files missing
        (repo / "SOP.md").write_text(
            "# SOP\n<!-- docs-evidence\nverified: 2026-01-01\n"
            "checks:\n  - name: deliberately broken\n    run: exit 3\n"
            "  - name: also broken\n    run: test -f definitely-not-here\n"
            "  - name: third\n    run: false\n-->\n")
        results = {
            "tier1 (presence)": tier1_presence(repo),
            "tier2 (changelog)": tier2_changelog(repo, ["src/app.py"]),
            "tier3 (evidence)": tier3_evidence(repo),
        }
    print()
    passed = all(v is False for v in results.values())
    for k, v in results.items():
        print(f"  {k}: {'correctly FAILED' if v is False else 'WRONGLY PASSED'}")
    print()
    print("negative control:", "PASS (the gate can fail)" if passed
          else "BROKEN (a tier passed when it must not)")
    return passed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--tier", type=int, choices=[1, 2, 3], action="append")
    ap.add_argument("--changed-files", help="file with one changed path per line")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return 0 if self_test() else 1

    repo = Path(a.repo).resolve()
    tiers = a.tier or [1, 2, 3]
    changed = None
    if a.changed_files and os.path.exists(a.changed_files):
        changed = [ln.strip() for ln in open(a.changed_files) if ln.strip()]

    print(f"docs-check: {repo.name}  tiers={tiers}")
    good = True
    if 1 in tiers:
        print("\n[tier 1] required docs present"); good &= tier1_presence(repo)
    if 2 in tiers:
        print("\n[tier 2] changelog on code change"); good &= tier2_changelog(repo, changed)
    if 3 in tiers:
        print("\n[tier 3] SOP evidence still true"); good &= tier3_evidence(repo)
    print("\nRESULT:", "pass" if good else "FAIL")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
