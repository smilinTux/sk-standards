# Caller Identity Header Standard

**Status:** PROPOSED. Ecosystem standard for every `sk*` service, worker and tool that
sends an inference request to `skgateway`. The headers go to `skgateway` only: a request
to any other endpoint carries none of them (section 2.4).
**Date:** 2026-11-12
**Scope:** the attribution headers a caller adds to a gateway request so the request can
be tied to a service, an agent, a session and a coord card. Not how the gateway routes
(that is the skmodels registry and the routing headers named in section 4), not who is
allowed to call (that is [`SKWORLD_AUTHORIZATION_STANDARD`](./SKWORLD_AUTHORIZATION_STANDARD.md)),
and not how an agent subject is spelled across stores
(that is [`IDENTITY_NAMING_STANDARD`](./IDENTITY_NAMING_STANDARD.md)).

> One sentence: **a caller labels the request it already makes with four
> attribution-only headers (`x-app`, `x-sk-card-id`, `x-sk-caller-agent`,
> `x-sk-caller-session`), omits any value it does not know, and never uses a routing
> header to say who it is.**

---

## 1. Why this exists: nobody can say who spent what

The gateway writes one `request_log` row per request into its `metrics.db`. A baseline
taken on 2026-11-11 found **0% of rows with a caller identity and under 1% with a known
cost**. The gateway's own code says why (`src/index.mjs:2549-2560` at the commit cited
in section 4): Claude Code sends only a shared bearer literal, a `user-agent` and
`x-app: cli`, and the skos, skcapstone, skchat and Hermes callers send `Content-Type`
and nothing else. The gateway is not dropping an identity. Nothing sends one.

Without attribution, tokens per service, per agent, per session and per closed card
cannot be measured, so no SKRSI loop can say whether a change made anything cheaper.

The obvious fix, "send `x-agent-id` and `x-session-id`", is wrong. On current gateway
main those two headers are **routing inputs**: one can pin the model and filter
backends, the other reorders bucket members (section 4). A caller that added them only
to be counted would silently change where its requests go. This standard therefore
defines a separate set of headers that the gateway reads for attribution and for
nothing else.

---

## 2. The four attribution headers

| Header | Meaning | Value format | Where the caller gets it | Example |
|---|---|---|---|---|
| `x-app` | The calling service, optionally with one component | `^[a-z][a-z0-9-]{0,31}(\.[a-z][a-z0-9-]{0,31})?$` | A constant in the caller's code: the service (repo) name, plus `.component` when one service makes calls for several jobs | `skos.triage`, `skmemory.dream`, `skwhisper` |
| `x-sk-card-id` | The coord card the work is for | `^[0-9a-f]{8}$` (8 lowercase hex, the short card id) | The environment variable `SKFLEET_CARD_ID`, read once at start. Only when it is set | `f5f44ded` |
| `x-sk-caller-agent` | The declared agent the caller acts as | `^[a-z][a-z0-9-]{0,62}$` | The skmemory resolver `get_active_agent()` (section 2.1), read once at process start | `lumina` |
| `x-sk-caller-session` | A minted random id that groups the requests of one session or one work cycle | `^[0-9a-f]{16,64}$` (lowercase hex only) | Inherited from `SKFLEET_SESSION_ID` when it is set, otherwise minted (section 2.2) | `0b7c2a4e6f1d4c399a512f6e8d1c7b90` |

The two environment variables already exist. The fleet dispatcher sets `SKFLEET_CARD_ID`
and `SKFLEET_SESSION_ID` in every worker's environment, and verifies them on the worker's
process tree (skcapstone `scripts/fleet/skfleet-rotate.py`, `expected_env` in
`_pi_process_attributed`, and `scripts/fleet/skfleet-worker-wrapper.py`, `expected_env`).
A helper reads them; it never asks coord which card it is on.

Rules that apply to every value:

- **Omit, never guess.** A header whose value the caller does not know is left out. It is
  never sent empty, never sent as a placeholder (`unknown`, `none`, `anonymous`,
  `default`), and never filled from a fallback.
- **Lower-case, then validate; omit if it still does not match.** The helper lower-cases
  every value first (the gateway already lower-cases agent ids when it normalizes them,
  so the canonical form keeps one agent under one key). It then checks the value against
  the format. A value that still does not match is omitted, never truncated or otherwise
  rewritten. A malformed header is worse than a missing one, because it looks like data.
  The one derivation this standard defines is the session hash in section 2.2.

### 2.1 `x-sk-caller-agent` is resolved, never assumed

The value is what skmemory's `get_active_agent()` returns, resolved the way
[`SKMEMORY_NODE_CONFIG_STANDARD`](./SKMEMORY_NODE_CONFIG_STANDARD.md) section 2
describes: the three selectors `SKAGENT`, `SKCAPSTONE_AGENT` and `SKMEMORY_AGENT` (any
that are set must agree), then the declared `SK_DEFAULT_AGENT`, then a sole installed
agent. When the resolver returns `None`, **the header is omitted**. There is no implicit
default agent, and a caller that writes `lumina` because "it is usually lumina" creates
exactly the false attribution this standard exists to prevent.

A caller that cannot import skmemory may read the same declared selectors itself, with
the same agreement rule. It must not invent a third rule, and in particular it must not
fall back to `lumina` or to any other name when the selectors are unset.

**No hostnames (normative).** The agent format is a plain lowercase name, so it cannot
tell an agent name from a node name or a user name: a host called `node07` matches it.
The format check is therefore not enough. The value must be the declared agent name the
resolver returned, and a caller must never put a hostname, a node name, a user name or
anything derived from them in this header, even when it matches the format.

### 2.2 `x-sk-caller-session` is a minted random id

The session id carries no meaning. Readers only group by it and count. Its format admits
lowercase hex and nothing else, so a hostname, an IP address, a path, a worktree name or
prompt text cannot be expressed in it: a value such as `198.51.100.7` or
`node07:tmux-3` fails the format and is omitted. That exclusion holds by construction
for this header only.

Where the value comes from, in order:

1. **Inherited, when `SKFLEET_SESSION_ID` is set.** Interactive and fleet sessions run
   inside a dispatched session inherit it, so every process of that session sends the
   same id. A value that already matches the format (after lower-casing) is sent as is.
   Any other value is replaced by the first 32 hex characters of the SHA-256 of its
   UTF-8 bytes. This is needed today: the dispatcher names a worker session after its
   lane and card (`sess="%s%s"%(_LANE["prefix"],cid)` in
   `scripts/fleet/skfleet-rotate.py`, for example `codex-auto-` plus the card id), which
   is not opaque. The hash keeps one id per session with no coordination between
   processes, and what it is derived from (a lane name and a card id) is already sent in
   the clear as `x-sk-card-id`, so it hides nothing that matters and leaks nothing new.
2. **Minted per interactive session,** when no `SKFLEET_SESSION_ID` is set: one random id
   at session start, for example `uuid.uuid4().hex` or `secrets.token_hex(16)` in Python.
3. **Minted per work cycle, for daemons and timers.** A long-lived process mints a new id
   at the start of each unit of work: one skwhisper digest pass, one watchdog tick, one
   timer run. Never one id for the life of the process, because a daemon that runs for
   weeks would group unrelated work under one key. Never one id per request either,
   because then the id groups nothing.

A runtime's own session id is never sent as this header, even when it looks opaque. Mint
one, and keep a mapping on the caller's side if it is needed.

### 2.3 Example request

An skos triage call made for a card, by the declared agent, inside one run:

```http
POST /v1/chat/completions HTTP/1.1
Content-Type: application/json
x-app: skos.triage
x-sk-card-id: f5f44ded
x-sk-caller-agent: lumina
x-sk-caller-session: 0b7c2a4e6f1d4c399a512f6e8d1c7b90

{"model": "sk-default", "messages": [ ... ]}
```

The same call made by a timer with no card and no resolvable agent sends only
`x-app: skos.triage` and, if the run minted one, `x-sk-caller-session`. That request is
still correct.

### 2.4 Attach the headers only when the target is skgateway

A caller attaches the attribution headers **only when the request goes to skgateway**,
and otherwise sends none of the four. Many callers can be pointed at another endpoint (a
direct model server, a third-party provider, a test double), and a label meant for the
gateway's `metrics.db` must not travel there.

**The signal is the `SKGATEWAY_URL` environment variable.** A request goes to skgateway
when the origin (scheme, host and port) of the URL the caller is about to call equals
the origin of `SKGATEWAY_URL`. When `SKGATEWAY_URL` is unset, its value is the estate
default `http://localhost:18780`. The path is ignored, because current callers disagree
on whether the variable ends in `/v1`. The host names `localhost`, `127.0.0.1` and `::1`
count as the same host. Anything else is not the gateway, and the helper returns no
headers.

Why this signal: it is the one most callers already read. skos reads `SKGATEWAY_URL` in
`src/skos/gtd_triage.py:35`, `src/skos/watchdog/headline.py:40`,
`src/skos/watchdog/grader.py:56`, `src/skos/adapters/order.py:38` and
`src/skos/task_triggers.py:369`; skcapstone in `src/skcapstone/skgateway_client.py:19`;
skchat in `src/skchat/agent_model.py:97`. Their defaults are `http://localhost:18780/v1`
or `http://localhost:18780`, which is why the comparison is by origin. Callers that take
their URL from another setting still compare it with `SKGATEWAY_URL`:

- skos `src/skos/mail.py:93` takes its URL from `GTD_LLM_URL` (default the gateway on
  `127.0.0.1:18780`). It attaches the headers when that URL's origin matches.
- skmemory `skmemory/triage.py:109` uses the constant `DEFAULT_GATEWAY_URL`
  (`http://localhost:18780/v1`), passed in as `base_url`. It compares `base_url`.
- skwhisper takes its summarizer endpoint from the `summarize_url` setting
  (`skwhisper/config.py`), whose default today is not the gateway. Until that setting
  points at the gateway, skwhisper sends no attribution headers, which is correct.

`SK_GATEWAY_URL` (with an underscore), read by one skcapstone helper script
(`src/skcapstone/data/sk-pi-gateway-sync.py`), is not the signal. A caller must not
decide "this is the gateway" from a hostname list, a port alone or a model name.

---

## 3. How callers add them: one field group, no new call

1. **Add the headers to the request the caller already makes.** No extra request, no
   registration call, no lookup against the gateway, coord or skmemory at request time.
2. **Resolve once, reuse.** The agent, `SKFLEET_CARD_ID` and the gateway check are
   resolved when the process starts and kept in memory. The session id is inherited or
   minted once per session, or once per work cycle for a daemon (section 2.2). Building
   the header group is a dictionary merge.
3. **Never block and never fail on a missing value.** A caller that cannot resolve an
   agent, has no card, or has no session sends the request without that header. No
   retry, no wait, no warning per request. One log line at start up is enough.
4. **Never change the request body for attribution.** Model, messages and parameters are
   exactly what they would be without this standard.
5. **Keep it in one helper per language or repo,** so a format change is one edit. The
   helper returns only the headers it has values for.

This keeps SKRSI rule 1 (no synchronous additions) and rule 2 (one field group on an
existing write, never an extra call).

---

## 4. The attribution headers change neither routing nor authorization

Everything in this section was read on `skgateway` main at commit
**`762ac1a74b350ffb25597c8d5085e5ab93dac45d`**. Line numbers are at that commit.

### 4.1 What the gateway does with each attribution header today

| Header | Read at | Effect | Routing or auth effect |
|---|---|---|---|
| `x-app` | `src/index.mjs:2625` | Copied into `attribution.client`, which lands in the `request_log.client` column (declared at `src/metrics/collector.mjs:220`) | None. `src/index.mjs:2625` is the only read of `x-app` in `src/`. The other matches are a comment (`src/index.mjs:2553`) and the column declaration and its doc comment in `collector.mjs`. |
| `x-sk-card-id` | `src/index.mjs:2661`, `src/index.mjs:2750` | Written to `energy_log.card_id` (`src/metrics/collector.mjs:283`) and carried on the router request as `cardId` | None. Listed first in `INTERNAL_CONTROL_HEADERS` (`src/proxy/router.mjs:161`), so it is stripped before any upstream call (`src/proxy/router.mjs:4366`). |
| `x-sk-caller-agent` | Not read anywhere | Ignored until card P3.5 | None |
| `x-sk-caller-session` | Not read anywhere | Ignored until card P3.5 | None |

### 4.2 Routing headers: do NOT add these for attribution

These headers already exist and the gateway acts on them. A caller that sends one of
them is asking for a routing or access behaviour, whatever it meant.

| Header | What it does on the gateway | Code (at `762ac1a`) |
|---|---|---|
| `x-agent-id` | **Pins the model.** The router looks up a registry context `agent:<id>` and, when one exists and the request sets no context, service or role, replaces the requested model with the pinned target and rewrites the body. | `src/proxy/router.mjs:2429-2435` (`resolveAgentTarget`), `src/proxy/router.mjs:3591-3605` (the pin) |
| `x-agent-id` | **Filters backends.** A backend with `allowed_agents` set is skipped for any other agent id. | `src/proxy/router.mjs:968`, `src/proxy/router.mjs:1179-1182` (`allowsAgent`), used at `:1968`, `:2015`, `:2306` |
| `x-agent-id` | **Passes the identity gate.** With `identity.require_agent_id` on, a request with no agent id gets a 403. The header alone turns `method` from `anonymous` to `header`. | `src/index.mjs:1073`, `src/index.mjs:2352-2358`, `src/index.mjs:2385-2395` |
| `x-session-id` | **Reorders bucket members.** It becomes the bucket affinity key, so the remembered member is tried first. | `src/policy/bucket-affinity.mjs:44-47`, `src/proxy/router.mjs:3236-3244` |
| `x-session-id` | Becomes the identity's `session_id` and the router audit session. | `src/index.mjs:2357`, `src/index.mjs:2740`, `src/identity/capauth.mjs:407` |
| `x-sk-service` | **Selects a registry route.** Precedence is context, then service, then role. A set service also disables the per-agent pin above. | `src/index.mjs:2745`, `src/proxy/router.mjs:3587-3594` |

Authorization is not affected by any header in either table. The authorization PDP takes
its subject from `subjectFromIdentity()`, which returns an empty subject (deny) for any
identity that is not cryptographically verified, so an `x-agent-id` claim is never a
policy subject (`src/policy/authz_routes.mjs:121-123`). The attribution headers are not
part of the identity at all.

### 4.3 Callers that already use a routing header on purpose

Some callers send `x-session-id` or `x-agent-id` deliberately: skharness puts
`x-session-id` on Pi worker requests so a session stays on one bucket member, and its Pi
harness sends `x-agent-id`. Those uses are routing decisions and stay where they are.
This standard does not remove them. It adds the attribution headers next to them, and
card P3.5 reconciles the overlap so one value is not sent twice under two meanings.

### 4.4 The rule for the gateway side

The gateway **must not** read `x-app`, `x-sk-card-id`, `x-sk-caller-agent` or
`x-sk-caller-session` for routing, backend selection, quotas, rate limits, admission,
authentication or authorization. They are unverified labels and are recorded as such. A
change that wants to route on caller identity uses the routing headers or the verified
identity, and says so in its own card.

---

## 5. Values are metadata only

- A value is a label: a service name, an agent name, a short card id, an opaque id. It
  never carries a prompt, a response, memory content, a credential, a token, a DSN, a
  private hostname, an IP address, a file path or a user's personal data.
- **The gateway forwards unknown headers upstream today.** On `762ac1a`, only
  `x-sk-card-id` of the four is in `INTERNAL_CONTROL_HEADERS`
  (`src/proxy/router.mjs:160-187`); `x-app`, `x-sk-caller-agent` and
  `x-sk-caller-session` are forwarded to the backend like any other header. Card P3.5
  adds `x-sk-caller-agent` and `x-sk-caller-session` to `INTERNAL_CONTROL_HEADERS`, so
  they never leave the gateway. `x-app` stays forwarded, because some clients set it for
  their own reasons (Claude Code sends `x-app: cli`), and its values are public service
  names.
- **Sequencing (normative).** P3.5's strip of `x-sk-caller-agent` and
  `x-sk-caller-session` is merged **and deployed** before any caller sends them. The
  caller cards P3.2, P3.3 and P3.4 depend on P3.5 and do not merge until that deploy is
  live, so no third-party upstream ever receives either header. A caller may ship
  `x-app` and `x-sk-card-id` support earlier, since the gateway already handles both.
- The gateway stores the values in its local `metrics.db` only. SKRSI readers aggregate
  them into counts and sums; they do not export raw session ids off the node.

---

## 6. What the gateway records, today and after P3.5

| Header | Recorded today (`762ac1a`) | Recorded after card P3.5 merges and deploys |
|---|---|---|
| `x-app` | `request_log.client` | Unchanged |
| `x-sk-card-id` | `energy_log.card_id` only, when an energy row is written | Also a new `request_log.card_id` column, on the existing terminal row write |
| `x-sk-caller-agent` | Nothing | `request_log.agent_id` (`src/metrics/collector.mjs:196`), **only when** the resolved identity is anonymous |
| `x-sk-caller-session` | Nothing | `request_log.session_id` (`src/metrics/collector.mjs:199`), **only when** the resolved identity is anonymous and has no `session_id` |

### 6.1 Precedence: the caller headers fill only an anonymous identity

"Anonymous" means the identity the gateway resolved has `method` `anonymous`
(`src/index.mjs:2353-2358`, the same test the `require_agent_id` gate uses at
`src/index.mjs:2385`). A verified CapAuth identity and an `x-agent-id` header both give a
non-anonymous identity, so they always win for `agent_id`. For `session_id`, an
identity's own `session_id` (from `x-session-id` or the verified identity) also wins. The
caller headers fill `agent_id` and `session_id` only when the resolved identity is
anonymous, so existing rows keep the meaning they had.

### 6.2 The P3.5 constraint: the fallback never reaches routing

The `x-sk-caller-agent` fallback applies **only at the `request_log` write**. It never
changes `metricsAgentId` (defined at `src/index.mjs:2565`). That value is also the
router's `agentId` (`src/index.mjs:2737`), which drives the per-agent model pin and the
`allowed_agents` backend filter (section 4.2), and it is what `energy_log.agent_id`
records. A P3.5 change that copied `x-sk-caller-agent` into `metricsAgentId` or into the
identity would turn an attribution header into a routing header, which section 4.4
forbids. P3.5 carries a test that a request with `x-sk-caller-agent: lumina` routes
exactly like the same request without it.

---

## 7. Conformance checks

A caller conforms when all of these hold. Each is checkable from the caller's own tests
with a captured request, with no gateway running.

| # | Check |
|---|---|
| C1 | Every gateway request the caller makes carries `x-app` matching the section 2 format. Exempt: a caller whose runtime owns the HTTP client and sets `x-app` itself (Claude Code sends `x-app: cli`). Such a caller sends whatever of the other headers its runtime lets it add, and never overrides the runtime's `x-app`. |
| C2 | `x-sk-card-id`, `x-sk-caller-agent` and `x-sk-caller-session` are present only with a value matching their format, and absent otherwise. A test with the agent unresolved shows the header absent, not empty. |
| C3 | `x-sk-caller-agent` equals what `get_active_agent()` returns in the test environment, lower-cased, when that matches the format. It is absent when the resolver returns `None`, and absent when the lower-cased value still does not match. |
| C4 | Adding the headers adds no request: the number of outbound calls in the test is unchanged. |
| C5 | The request body is byte-identical with and without the header helper. |
| C6 | No new `x-agent-id`, `x-session-id` or `x-sk-service` was added for attribution. Existing deliberate routing uses are named in the caller's docs. |
| C7 | No value contains a hostname, IP, path, prompt text or secret. The test asserts every format regex. For `x-sk-caller-session` the hex format excludes all of these by construction. For `x-app` and `x-sk-caller-agent` it does not (a node name can match), so the test also asserts that `x-app` is a constant in the caller's code and that the agent value is exactly the resolver's result. |
| C8 | A request whose target origin differs from the `SKGATEWAY_URL` origin (section 2.4) carries none of the four headers. |
| C9 | A daemon or timer mints a new `x-sk-caller-session` per work cycle: two cycles in the test send two different ids, and the requests of one cycle share one. |

---

## 8. Anti-patterns

| Anti-pattern | Why it is wrong |
|---|---|
| Sending `x-agent-id: lumina` "so the spend is attributed" | Pins the model to whatever `agent:lumina` maps to in the registry and may skip backends. Attribution changed routing. |
| Sending `x-session-id` from a one-shot timer job | Creates affinity state for a session that never continues, and moves bucket picks for no reason. |
| `x-sk-caller-agent: unknown` or a hard-coded default agent | A guess recorded as a fact. Omit the header. |
| Calling coord or skmemory per request to look up the card or agent | An extra call on the hot path. Resolve once at start. |
| Using the hostname or worktree path as the session id | A private name forwarded to an upstream provider. Use an opaque id. |
| Failing or retrying a request because a value is missing | Attribution is advisory. A missing label never costs a request. |

---

## Compliance line (put in your SOP + README)

> Gateway calls carry the attribution headers of `CALLER_IDENTITY_HEADER_STANDARD`
> (`x-app`, plus `x-sk-card-id`, `x-sk-caller-agent` and `x-sk-caller-session` when
> known) on the existing request, and no routing header is added for attribution.

---

## Related standards

- [`SKMEMORY_NODE_CONFIG_STANDARD`](./SKMEMORY_NODE_CONFIG_STANDARD.md): how the
  declared agent is set and resolved; the source of `x-sk-caller-agent`.
- [`IDENTITY_NAMING_STANDARD`](./IDENTITY_NAMING_STANDARD.md): canonical subject
  shapes. The attribution agent is a bare declared name, not a verified subject.
- [`SKWORLD_AUTHORIZATION_STANDARD`](./SKWORLD_AUTHORIZATION_STANDARD.md): the PDP that
  these headers never feed.
- [`INFERENCE_FEDERATION_STANDARD`](./INFERENCE_FEDERATION_STANDARD.md): the gateway's
  lanes and per-estate spend accounting, which attribution makes measurable.
- [`OBSERVABILITY_AND_SCHEDULING_STANDARD`](./OBSERVABILITY_AND_SCHEDULING_STANDARD.md):
  how the out of band collectors that read these columns are scheduled.
