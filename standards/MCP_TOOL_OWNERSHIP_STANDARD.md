# MCP Tool Ownership Standard

**Status:** Ecosystem standard for all `sk*` repos that expose an MCP server.
Companion to [`SKWORLD_MODULE_CONTRACT_STANDARD`](./SKWORLD_MODULE_CONTRACT_STANDARD.md)
and [`ARCHITECTURE_AND_DATAFLOW_STANDARD`](./ARCHITECTURE_AND_DATAFLOW_STANDARD.md).

**Why:** Multiple SKWorld services expose MCP tool surfaces to the same agents
(Claude Code, the Telegram bridges, Atlas). When the *same tool name* is defined
independently in more than one server, the behavior an agent gets depends on which
server answered, the implementations drift apart, and a bug fixed in one is missed
in the others. This standard fixes **one owning repo per tool** (the canonical
implementation) and says how the other servers may re-expose it.

---

## The rule: one owner, delegates never reimplement

1. **Every MCP tool name has exactly one OWNER repo** — the repo whose domain the
   tool belongs to, holding the canonical implementation.
2. **A non-owner server MAY re-expose an owned tool, but only as a thin DELEGATE**
   that calls the owner's library (or the owner's service), never a second copy of
   the logic. Same name + same `inputSchema` as the owner.
3. **Prefer drop over delegate** when no consumer needs the tool on the non-owner
   surface. A delegate is justified only when agents reach that server and not the
   owner's (e.g. the skcapstone aggregate MCP is the bridges' single surface).
4. **The owner's schema is the source of truth.** If a delegate's `inputSchema`
   drifts from the owner's, the owner wins (reconcile the delegate).

---

## Ownership table (inventory 2026-08-06)

Live surfaces measured: **skcapstone 125 tools · skchat 55 · skmemory 25** = 192
distinct names, **13 duplicated** across servers. Owners assigned by domain:

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
| `telegram_import` | skcapstone, skmemory | **skcapstone** | skmemory = **drop** (subset; skcapstone owns the full 8-tool telegram surface) |
| `telegram_import_api` | skcapstone, skmemory | **skcapstone** | skmemory = **drop** |
| `telegram_setup` | skcapstone, skmemory | **skcapstone** | skmemory = **drop** |
| `telegram_catchup` | skcapstone, skmemory | **skcapstone** | skmemory = **drop** |

**Single-owner clusters (no action, recorded for completeness):**
- `telegram_send`, `telegram_poll`, `telegram_chats`, `telegram_soul_swap` — skcapstone only (complete the telegram owner set).
- skchat-only: calling/WebRTC (`call_peer`, `initiate_call`, …), presence/typing, reactions, file-transfer — **skchat** owns the messaging plane.
- skmemory-only: `memory_promote`, `memory_consolidate`, `memory_synthesize_*`, `memory_graph`, … — **skmemory** owns the memory lifecycle.

## Domain ownership (the assignment rule, so new tools land right)

- **Messaging / chat / calls / presence → skchat.**
- **Memory store / search / recall / lifecycle → skmemory.**
- **Telegram bridge (import + send + setup + soul-swap) → skcapstone** (it holds
  the full bridge surface and the bridges run there).
- **Coordination / ITIL / CMDB → skcoord** (via skcapstone's aggregate server;
  see [`ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD`](./ITIL_AND_RUNBOOK_OPERATING_MODEL_STANDARD.md)).
- **Identity / trust / capauth → capauth.**

## Migration posture (how to converge without breaking consumers)

The **delegate** rows are already effectively delegates in skcapstone
(`mcp_tools/memory_tools.py`, `chat_tools.py` call the owning libraries), so they
are compliant as-is; the standard just fixes the direction so they can never
re-fork. The **drop** rows (skmemory's 4 telegram tools) are the only behavioral
change: they are a strict subset of skcapstone's telegram surface, so dropping
them from skmemory's `list_tools` is safe once any skmemory-only consumer is
confirmed to reach the skcapstone surface. That drop is a **gated follow-up**
(one skmemory release), not part of the inventory commit.

## Compliance checklist (per MCP-exposing repo)

- [ ] Every tool your server exposes is either OWNED here or a documented thin delegate.
- [ ] No delegate reimplements the owner's logic; schema matches the owner byte-for-byte.
- [ ] New tools are placed by the domain-ownership rule above; if a name already
      exists in another server, you delegate or pick a distinct name.
- [ ] Duplicates you cannot delegate are dropped in your next release with a note.
