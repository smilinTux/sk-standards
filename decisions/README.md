# Architecture Decision Records (ADRs)

This directory contains the accepted architecture decisions for the SKWorld estate.

## Number Allocation Rule

**READ THIS BEFORE CREATING A NEW ADR.**

ADR numbers are allocated on a first-come, first-served basis based on the **lowest unused PR number**:

1. Before claiming an ADR number, check all open pull requests on the `smilinTux/sk-standards` repository to see if any PR already claims that number.
2. The lowest-numbered open PR that claims a given ADR number **keeps the claim**.
3. If your PR would conflict with a lower-numbered PR, choose the next available number.
4. This rule exists because there is no central ownership of the identifier number space. Multiple authors can and do pick the same number without seeing each other's work.

### Why this rule matters

The ADR-0003 collision (September 2026) demonstrates the problem:
- PR 34, PR 36, and PR 39 all claimed ADR-0003
- All were authored by the same person but on different branches
- The lowest-numbered PR (34) kept the claim
- PR 36 became ADR-0004, PR 39 became ADR-0005

Following this rule prevents wasted renumbering work.

## How to check for conflicts

```bash
# List all PRs that add ADR files
gh pr list --repo smilinTux/sk-standards --search "ADR" --json number,title

# Or check the decisions directory on main
ls decisions/ | grep ADR
```

Choose the next sequential number that is not in use on `main` and not claimed by any open PR.

## ADR format

Follow the header format from `ADR-0001`:

```markdown
# ADR-NNNN: Short title

**Status:** Accepted | Proposed | Deprecated | Superseded
**Date:** YYYY-MM-DD
**Deciders:** Name1, Name2
**Extends:** [`ADR-XXXX`](./ADR-XXXX.md)
**Purpose:** One sentence explaining the decision's goal.
```

- **Status**: Most new ADRs start as `Proposed`. Change to `Accepted` when the decision is final.
- **Date**: The date the decision was made (for `Accepted`) or proposed (for `Proposed`).
- **Deciders**: The people who made the decision.
- **Extends**: Link to any ADRs this one builds upon.
- **Purpose**: A single sentence explaining what this ADR decides.

## Contents

An ADR should answer:

1. **Context**: What problem are we solving? What are the constraints?
2. **Decision**: What did we decide? Be precise.
3. **Rejected options**: What alternatives did we consider and reject? Why?
4. **Consequences**: What does this decision mean for the estate? What must change?

See `ADR-0001`, `ADR-0002`, or any accepted ADR for a complete example.
