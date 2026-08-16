# MCP Tool Ownership Standard

**Status:** Ecosystem standard for all `sk*` repos that expose an MCP server.
Companion to [`SKWORLD_MODULE_CONTRACT_STANDARD`](./SKWORLD_MODULE_CONTRACT_STANDARD.md),
[`ARCHITECTURE_AND_DATAFLOW_STANDARD`](./ARCHITECTURE_AND_DATAFLOW_STANDARD.md),
and [`SKWORLD_AUTHORIZATION_STANDARD`](./SKWORLD_AUTHORIZATION_STANDARD.md).

**Why:** Multiple SKWorld services expose MCP tool surfaces to the same agents
(Claude Code, the Telegram bridges, Atlas). When the *same tool name* is defined
independently in more than one server, the behavior an agent gets depends on which
server answered, the implementations drift apart, and a bug fixed in one is missed
in the others. This standard fixes **one owning repo per tool** (the canonical
implementation) and says how the other servers may re-expose it.

---

## The rule: one owner, delegates never reimplement

1. **Every MCP tool name has exactly one OWNER repo:** the repo whose domain the
   tool belongs to, holding the canonical implementation.
2. **A non-owner server MAY re-expose an owned tool, but only as a thin DELEGATE**
   that calls the owner's library (or the owner's service), never a second copy of
   the logic. Same name + same `inputSchema` as the owner.
3. **Prefer drop over delegate** when no consumer needs the tool on the non-owner
   surface. A delegate is justified only when agents reach that server and not the
   owner's (e.g. the skcapstone aggregate MCP is the bridges' single surface).
4. **The owner's schema is the source of truth.** If a delegate's `inputSchema`
   drifts from the owner's, the owner wins (reconcile the delegate).
5. **A delegate delegates the DECISION too.** An MCP tool handler is a Policy
   Enforcement Point, so it runs the
   [`SKWORLD_AUTHORIZATION_STANDARD` section 1](./SKWORLD_AUTHORIZATION_STANDARD.md#1-one-pdp-many-thin-peps)
   lifecycle against the one PDP. A delegate MUST NOT apply a second, locally
   invented authorization rule on top of the owner's: two servers exposing one
   tool name under two different capability gates is the same drift as two
   implementations, with a worse failure mode.

---

## Ownership table (point-in-time inventory, 2026-08-06)

**Read this table as a snapshot, not as a live measurement.** The tool COUNTS
below were measured once, on 2026-08-06, and every server has shipped since. The
OWNER and disposition columns are the normative part and do not expire; the
numbers are context. Re-measure before quoting them (enumerate each server's
`list_tools` response) rather than citing this date as current.

Live surfaces measured on 2026-08-06: **skcapstone 125 tools, skchat 55,
skmemory 25** = 192 distinct names, **13 duplicated** across servers. Owners
assigned by domain:

| Tool | Duplicated in | OWNER | Disposition for the non-owner |
|------|---------------|-------|-------------------------------|
| `memory_store` | skcapstone, skmemory | **skmemory** | skcapstone = thin delegate to the memory engine (bridges need it on the aggregate surface) |
| `memory_search` | skcapstone, skmemory | **skmemory** | skcapstone = thin delegate |
| `memory_recall` | skcapstone, skmemory | **skmemory** | skcapstone = thin delegate |
| `send_message` | skcapstone, skchat | **skchat** | skcapstone = thin delegate to skchat |
| `check_inbox` | skcapstone, skchat | **skchat** | skcapstone = thin delegate |
| `skchat_send` | skcapstone, skchat | **skchat** | skcapstone = thin delegate |
| `skchat_inbox` | skcapstone, skchat | **skchat** | skcapstone = thin delegate |
| `skchat_group_create` | skcapstone, skchat | **skchat** | skcapstone = thin delegate |
| `skchat_group_send` | skcapstone, skchat | **skchat** | skcapstone = thin delegate |
| `telegram_import` | ~~skcapstone, skmemory~~ | **skcapstone** | skmemory = **DROPPED** (2026-08-06, skmemory `0ec531f`) |
| `telegram_import_api` | ~~skcapstone, skmemory~~ | **skcapstone** | skmemory = **DROPPED** |
| `telegram_setup` | ~~skcapstone, skmemory~~ | **skcapstone** | skmemory = **DROPPED** |
| `telegram_catchup` | ~~skcapstone, skmemory~~ | **skcapstone** | skmemory = **DROPPED** |

**Single-owner clusters (no action, recorded for completeness):**
- `telegram_send`, `telegram_poll`, `telegram_chats`, `telegram_soul_swap`: skcapstone only (complete the telegram owner set).
- skchat-only: calling/WebRTC (`call_peer`, `initiate_call`, and the rest), presence/typing, reactions, file-transfer. **skchat** owns the messaging plane.
- skmemory-only: `memory_promote`, `memory_consolidate`, `memory_synthesize_*`, `memory_graph`, and the rest of the lifecycle. **skmemory** owns the memory lifecycle.

## Domain ownership (the assignment rule, so new tools land right)

- **Messaging / chat / calls / presence:** skchat.
- **Memory store / search / recall / lifecycle:** skmemory.
- **Telegram bridge (import + send + setup + soul-swap):** skcapstone (it holds
  the full bridge surface and the bridges run there).
- **Coordination / ITIL / CMDB:** skcoord (via skcapstone's aggregate server;
  see [`ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD`](./ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md)).
- **Identity / trust / capauth:** capauth.

This list is the tie-breaker for a NEW tool name. A domain not listed here is
not a licence to duplicate: assign it to the repo that owns the underlying
data, record the assignment in this table, and add the row in the same PR.

## Migration posture (how to converge without breaking consumers)

The **delegate** rows are already effectively delegates in skcapstone
(`mcp_tools/memory_tools.py`, `chat_tools.py` call the owning libraries), so they
are compliant as-is; the standard just fixes the direction so they can never
re-fork. The **drop** rows (skmemory's 4 telegram tools) were the only behavioral
change: they are a strict subset of skcapstone's telegram surface (both call the
same `skmemory.importers.telegram*` library), and the agents that reach
skmemory-mcp also have skcapstone-mcp. **DONE 2026-08-06** (skmemory `0ec531f`):
skmemory's `list_tools`/dispatch dropped the 4 wrappers, importer library
untouched, surface 25 to 21, tests green.

## Compliance checklist (per MCP-exposing repo)

- [ ] Every tool your server exposes is either OWNED here or a documented thin delegate.
- [ ] No delegate reimplements the owner's logic; schema matches the owner byte-for-byte.
- [ ] No delegate adds a second authorization rule of its own; the PDP decides once.
- [ ] New tools are placed by the domain-ownership rule above; if a name already
      exists in another server, you delegate or pick a distinct name.
- [ ] Duplicates you cannot delegate are dropped in your next release with a note.
- [ ] A new owner assignment is added to the table in this standard in the same PR
      that ships the tool, so the inventory does not silently go stale.

---

## Related standards

- [SKWORLD_AUTHORIZATION_STANDARD](./SKWORLD_AUTHORIZATION_STANDARD.md): an MCP
  tool handler is a PEP; ownership decides who implements, that standard decides
  who may call.
- [SKWORLD_MODULE_CONTRACT_STANDARD](./SKWORLD_MODULE_CONTRACT_STANDARD.md): the
  per-subapp manifest, the other place a subapp declares a surface.
- [ARCHITECTURE_AND_DATAFLOW_STANDARD](./ARCHITECTURE_AND_DATAFLOW_STANDARD.md):
  diagram the delegate direction so the owner is readable from the picture.

---

*License: Apache-2.0. Part of [sk-standards](../README.md); the skstacks copies
carry a "canonical home" pointer back here.*
