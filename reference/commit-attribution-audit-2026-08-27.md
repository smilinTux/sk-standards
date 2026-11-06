# Commit co-author attribution audit, 2026-08-27

## Scope and method

Card `6a45c813` scanned the complete reachable history in the local clones of
`sk-standards`, `skcapstone`, `skharness`, `skcoord`, and `capauth`. The scan
selected commits whose message contains a `Co-Authored-By: Claude` trailer.
The frozen scan result contained 1,156 matching commits: 32, 614, 208, 50, and
252 respectively.

A footer was treated as supported only when exact request or session evidence
available to the audit established a material Claude contribution. Author,
committer, lifecycle state, a card or PR link by itself, and the existence of a
footer were not treated as contribution evidence. On that basis, 1,155 matches
were suspected unsupported and one was not placed in the suspect set. This is
an evidence-availability classification, not a claim that the named contributor
definitively did no work.

The source audit and independent review are frozen under SKCapstone evidence:

- source audit SHA-256: `e5de40ecfd7069f6ab8223730ff1d300c5063d68ef57bd1a8170389e0e9019f7`
- independent review verdict SHA-256: `75e5603a052c30ac478cccd93edba2ae27271f154202fb4f97b8b0273f8d3e28`

## Results and classification

| Classification | Result | Append-only correction plan |
|---|---:|---|
| Codex-authored commit with Claude footer and no exact Claude contribution evidence | Approximately 300 | Record the commit in an audit note. Do not alter author or committer identity. Add a follow-up provenance correction only if repository owners request one. |
| Human-authored commit with Claude footer and no exact Claude contribution evidence | Approximately 850 | Mark as evidence unavailable, invite an exact request or session referent, and otherwise use an append-only provenance note. |
| Commit text identifies another producing agent while the footer credits Claude | At least 1 confirmed | Record the contradiction and evidence searched in an append-only note. Treat the footer as unsupported unless exact contrary evidence is produced. |
| Footer with support available to the audit | 1 outside the suspect set | Retain the history and preserve the supporting evidence referent. |

The approximate classes partition the 1,155 suspected commits only at audit
resolution. They must not be represented as exact per-commit verdict counts.
Each suspected commit inherits the plan for its class and remains individually
reclassifiable when exact evidence is produced.

## History and identity disposition

No merged public history was rewritten. No author or committer field was
changed. Any proposal to rewrite merged history is blocked pending explicit
approval that names the exact repository and commits. The default correction is
append-only documentation or a follow-up provenance commit, so existing clones,
signatures, and truthful author and committer identity remain intact.
