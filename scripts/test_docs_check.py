#!/usr/bin/env python3
"""Hermetic fixtures for docs_check public-claim evidence.

These are deliberately stdlib-only because the reusable docs gate installs no test
framework. They prove current source-bound inventories pass and stale or invented
public claims fail closed.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("docs_check.py")
SPEC = importlib.util.spec_from_file_location("docs_check", MODULE_PATH)
assert SPEC and SPEC.loader
DOCS_CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOCS_CHECK)


class PublicClaimEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        (self.repo / "docs").mkdir()
        (self.repo / "src").mkdir()
        (self.repo / "docs" / "API.md").write_text(
            "# API\n<!-- docs-claims:api_routes -->\n"
            "- `GET /health`\n- `POST /v1/chat/completions`\n"
            "<!-- /docs-claims:api_routes -->\n",
            encoding="utf-8",
        )
        (self.repo / "docs" / "CONFIGURATION.md").write_text(
            "# Configuration\n<!-- docs-claims:configuration_keys -->\n"
            "- `server.port`\n- `siem.enabled`\n"
            "<!-- /docs-claims:configuration_keys -->\n",
            encoding="utf-8",
        )
        (self.repo / "docs" / "SIEM.md").write_text(
            "# SIEM\n<!-- docs-claims:siem_event_types -->\n"
            "- `request`\n- `response`\n"
            "<!-- /docs-claims:siem_event_types -->\n",
            encoding="utf-8",
        )
        (self.repo / "src" / "public-claims.mjs").write_text(
            "export const PUBLIC_API_ROUTES = [\n"
            "  'GET /health',\n  'POST /v1/chat/completions',\n];\n"
            "export const PUBLIC_CONFIGURATION_KEYS = [\n"
            "  'server.port',\n  'siem.enabled',\n];\n"
            "export const EventType = Object.freeze({\n"
            "  REQUEST: 'request',\n  RESPONSE: 'response',\n});\n",
            encoding="utf-8",
        )
        manifest = {
            "version": 1,
            "bindings": [
                {
                    "kind": "api_routes",
                    "document": "docs/API.md",
                    "source": "src/public-claims.mjs",
                    "source_symbol": "PUBLIC_API_ROUTES",
                    "source_shape": "array",
                },
                {
                    "kind": "configuration_keys",
                    "document": "docs/CONFIGURATION.md",
                    "source": "src/public-claims.mjs",
                    "source_symbol": "PUBLIC_CONFIGURATION_KEYS",
                    "source_shape": "array",
                },
                {
                    "kind": "siem_event_types",
                    "document": "docs/SIEM.md",
                    "source": "src/public-claims.mjs",
                    "source_symbol": "EventType",
                    "source_shape": "object_values",
                },
            ],
        }
        (self.repo / "docs" / "source-evidence.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def check(self) -> tuple[bool, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = DOCS_CHECK.tier3_public_claims(self.repo)
        return result, output.getvalue()

    def test_current_source_bound_claims_pass(self) -> None:
        result, output = self.check()
        self.assertTrue(result, output)
        self.assertIn("exact route/key/event inventory equality only", output)

    def test_stale_documented_route_fails(self) -> None:
        path = self.repo / "docs" / "API.md"
        path.write_text(path.read_text().replace("GET /health", "GET /stale"))
        result, output = self.check()
        self.assertFalse(result)
        self.assertIn("missing_from_docs=['GET /health']", output)
        self.assertIn("not_in_source=['GET /stale']", output)

    def test_invented_configuration_key_fails(self) -> None:
        path = self.repo / "docs" / "CONFIGURATION.md"
        path.write_text(path.read_text().replace(
            "- `siem.enabled`", "- `siem.enabled`\n- `provider.secret_mode`"
        ))
        result, output = self.check()
        self.assertFalse(result)
        self.assertIn("not_in_source=['provider.secret_mode']", output)

    def test_stale_siem_event_type_fails(self) -> None:
        path = self.repo / "src" / "public-claims.mjs"
        path.write_text(path.read_text().replace(
            "  RESPONSE: 'response',", "  RESPONSE: 'response',\n  FAILOVER: 'failover',"
        ))
        result, output = self.check()
        self.assertFalse(result)
        self.assertIn("missing_from_docs=['failover']", output)

    def test_non_literal_source_inventory_fails(self) -> None:
        path = self.repo / "src" / "public-claims.mjs"
        path.write_text(path.read_text().replace(
            "  RESPONSE: 'response',", "  RESPONSE: computedEventType,"
        ))
        result, output = self.check()
        self.assertFalse(result)
        self.assertIn("must contain only literal string-valued entries", output)

    def test_source_path_escape_fails(self) -> None:
        manifest_path = self.repo / "docs" / "source-evidence.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["bindings"][0]["source"] = "../outside.mjs"
        manifest_path.write_text(json.dumps(manifest))
        result, output = self.check()
        self.assertFalse(result)
        self.assertIn("escapes the repository", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
